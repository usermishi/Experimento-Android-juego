#!/usr/bin/env python3
import os
import sys
import json
import logging
import traceback
import requests
from bs4 import BeautifulSoup
import yt_dlp
import re
from urllib.parse import urljoin

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DonghuaDownloader:
    def __init__(self):
        self.log_file = "donghua_error.log"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_page_content(self, url):
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error al acceder a {url}: {e}")
            raise

    def scrape_seasons_and_episodes(self, url):
        html = self.get_page_content(url)
        soup = BeautifulSoup(html, 'html.parser')

        seasons = {}
        # Selectores comunes para temporadas
        season_elements = soup.select('.seasons-container .season, .nav-tabs .nav-item, #season-select option, .season-list a')

        if not season_elements:
            seasons['Temporada 1'] = self.extract_episodes(soup, url)
        else:
            for i, el in enumerate(season_elements):
                name = el.get_text(strip=True) or f"Temporada {i+1}"
                seasons[name] = self.extract_episodes(soup, url)

        return seasons

    def extract_episodes(self, soup, base_url):
        episodes = []
        # Buscar enlaces que parezcan episodios (clases comunes o patrones de URL)
        links = soup.find_all('a', href=re.compile(r'episodio|episode|capitulo|cap-\d+'))

        # También buscar en contenedores comunes de listas de episodios
        ep_containers = soup.select('.episodes-list, .list-episodes, .ep-list, #episode-list')
        for container in ep_containers:
            links.extend(container.find_all('a'))

        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href')
            if href:
                href = urljoin(base_url, href)
                # Intentar extraer número de episodio de la URL o del texto
                num_match = re.search(r'(\d+)', title) or re.search(r'(\d+)', href.split('/')[-1])
                num = int(num_match.group(1)) if num_match else None

                if num is not None:
                    episodes.append({'number': num, 'url': href, 'title': title})

        # Eliminar duplicados por número
        unique_eps = {}
        for ep in episodes:
            if ep['number'] not in unique_eps:
                unique_eps[ep['number']] = ep

        return sorted(unique_eps.values(), key=lambda x: x['number'])

    def find_embed_urls(self, ep_url):
        """Busca iframes o embeds de servidores conocidos."""
        html = self.get_page_content(ep_url)
        soup = BeautifulSoup(html, 'html.parser')
        embeds = []

        # Buscar iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if src:
                if any(srv in src for srv in ['dailymotion.com', 'ok.ru', 'rumble.com', 'voe.sx', 'vidoza.net']):
                    if src.startswith('//'):
                        src = 'https:' + src
                    embeds.append(src)

        return embeds

    def download_episode(self, ep_data):
        print(f"\n>>> Procesando Episodio {ep_data['number']}...")

        # Intentar encontrar embeds primero si yt-dlp falla con la URL directa de la página
        target_urls = [ep_data['url']]
        try:
            embeds = self.find_embed_urls(ep_data['url'])
            if embeds:
                print(f"   Detectados {len(embeds)} servidores embebidos.")
                target_urls = embeds + target_urls
        except:
            pass

        # Opciones de yt-dlp optimizadas
        ydl_opts = {
            'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            'outtmpl': f'Donghua_Ep_{ep_data["number"]}.%(ext)s',
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
            # Forzar 480p si está disponible, si no, lo más cercano por debajo
            'format_sort': ['res:480', 'ext:mp4:m4a'],
        }

        success = False
        for url in target_urls:
            print(f"   Intentando descargar desde: {url}")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                success = True
                break
            except Exception as e:
                logger.warning(f"   Fallo con la URL {url}: {str(e)[:100]}...")
                continue

        if not success:
            raise Exception(f"No se pudo descargar el episodio {ep_data['number']} de ninguna fuente.")

    def run(self):
        try:
            print("========================================")
            print("   DONGHUA DOWNLOADER FOR TERMUX")
            print("========================================")
            url = input("Introduce la URL del Donghua: ").strip()
            if not url:
                return

            seasons = self.scrape_seasons_and_episodes(url)
            if not seasons:
                print("Error: No se detectaron episodios ni temporadas.")
                return

            season_names = list(seasons.keys())
            if len(season_names) > 1:
                print("\nTemporadas encontradas:")
                for i, name in enumerate(season_names):
                    print(f"  {i+1}. {name}")
                sel = int(input("\nSelecciona el número de la temporada: ")) - 1
                selected_season = season_names[sel]
            else:
                selected_season = season_names[0]
                print(f"\nTemporada: {selected_season}")

            episodes = seasons[selected_season]
            if not episodes:
                print("Error: La temporada seleccionada no tiene episodios detectables.")
                return

            print(f"Episodios disponibles: {episodes[0]['number']} al {episodes[-1]['number']} (Total: {len(episodes)})")

            start_ep = int(input(f"Episodio inicial: "))
            end_ep = int(input(f"Episodio final: "))

            to_download = [ep for ep in episodes if start_ep <= ep['number'] <= end_ep]

            if not to_download:
                print("No hay episodios en ese rango.")
                return

            print(f"\nIniciando cola de descarga ({len(to_download)} episodios)...")
            for ep in to_download:
                self.download_episode(ep)

            print("\n¡Todo listo! Las descargas han finalizado.")

        except Exception as e:
            self.handle_error(e)

    def handle_error(self, e):
        error_msg = traceback.format_exc()
        logger.error(f"Error fatal detectado.")
        print("\n" + "!"*40)
        print("   FALLO EN EL SCRIPT")
        print("!"*40)
        print("\nResumen del error:")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensaje: {e}")

        print("\nAnálisis detallado:")
        print(error_msg)

        opcion = input("\n¿Deseas exportar este informe de error a 'donghua_error.log'? (s/n): ").lower()
        if opcion == 's':
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("DONGHUA DOWNLOADER ERROR REPORT\n")
                f.write("="*30 + "\n")
                f.write(error_msg)
            print(f"\n[+] Log guardado en: {os.path.abspath(self.log_file)}")

if __name__ == "__main__":
    downloader = DonghuaDownloader()
    downloader.run()
