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

    def find_json_in_html(self, html):
        """Busca y extrae objetos JSON de etiquetas <script>."""
        scripts = BeautifulSoup(html, 'html.parser').find_all('script')
        found_data = []
        for script in scripts:
            if script.string:
                # Buscar patrones comunes de listas de episodios en JSON
                # Este regex busca algo que parezca un objeto o array JSON grande
                json_matches = re.findall(r'(\[.*\]|\{.*\})', script.string)
                for match in json_matches:
                    try:
                        data = json.loads(match)
                        # Verificar si parece contener episodios
                        str_data = str(data).lower()
                        if 'episodio' in str_data or 'episode' in str_data:
                            found_data.append(data)
                    except:
                        continue
        return found_data

    def scrape_seasons_and_episodes(self, url):
        html = self.get_page_content(url)
        soup = BeautifulSoup(html, 'html.parser')

        seasons = {}

        # Intentar extraer mediante JSON primero
        json_data_list = self.find_json_in_html(html)
        for data in json_data_list:
            # Buscar estructuras como {"seasons": [...]} o listas de episodios
            if isinstance(data, dict):
                if 'seasons' in data and isinstance(data['seasons'], list):
                    for i, s in enumerate(data['seasons']):
                        name = s.get('name', f"Temporada {i+1}")
                        s_url = urljoin(url, s.get('url', ''))
                        seasons[name] = {'url': s_url, 'episodes': []}
                elif 'episodes' in data and isinstance(data['episodes'], list):
                    # Si encontramos episodios directamente, los añadimos a una temporada por defecto
                    if 'Temporada 1' not in seasons:
                        seasons['Temporada 1'] = {'url': url, 'episodes': []}
                    for ep in data['episodes']:
                        num = ep.get('number') or ep.get('episode_number')
                        e_url = urljoin(url, ep.get('url', ep.get('link', '')))
                        if num and e_url:
                            seasons['Temporada 1']['episodes'].append({'number': int(num), 'url': e_url, 'title': ep.get('title', f"Episodio {num}")})

        if seasons:
            logger.info(f"Se detectaron {len(seasons)} temporadas vía JSON.")
            return seasons
        # Buscar contenedores de temporadas con enlaces
        season_links = soup.select('.seasons-container a, .nav-tabs a, .season-list a, .temporadas a')

        if not season_links:
            seasons['Temporada 1'] = {'url': url, 'episodes': self.extract_episodes(soup, url)}
        else:
            for i, link in enumerate(season_links):
                name = link.get_text(strip=True) or f"Temporada {i+1}"
                href = urljoin(url, link.get('href'))
                seasons[name] = {'url': href, 'episodes': []}

        return seasons

    def extract_episodes(self, soup, base_url):
        episodes = []
        # Buscar enlaces que parezcan episodios
        links = soup.find_all('a', href=re.compile(r'episodio|episode|capitulo|cap-\d+|/episode/'))

        # Añadir links de contenedores comunes
        for selector in ['.episodes-list', '.list-episodes', '.ep-list', '#episode-list', '.item-episode', '.views-field-title']:
            links.extend(soup.select(f"{selector} a"))

        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href')
            if href:
                href = urljoin(base_url, href)
                # Extraer número de episodio
                # Priorizar el final de la URL para evitar números de temporada o serie
                url_parts = href.rstrip('/').split('/')
                last_part = url_parts[-1]

                num_match = re.search(r'-x(\d+)', last_part) or re.search(r'(\d+)$', last_part) or re.search(r'(\d+)', title)
                num = int(num_match.group(1)) if num_match else None

                if num is not None:
                    episodes.append({'number': num, 'url': href, 'title': title})

        # Eliminar duplicados
        unique_eps = {}
        for ep in episodes:
            if ep['number'] not in unique_eps:
                unique_eps[ep['number']] = ep

        return sorted(unique_eps.values(), key=lambda x: x['number'])

    def find_embed_urls(self, ep_url):
        html = self.get_page_content(ep_url)
        soup = BeautifulSoup(html, 'html.parser')
        embeds = []

        # Buscar en iframes
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src:
                if any(srv in src for srv in ['dailymotion.com', 'ok.ru', 'rumble.com', 'voe.sx', 'vidoza.net']):
                    if src.startswith('//'): src = 'https:' + src
                    embeds.append(src)

        # Buscar en scripts (algunos cargan el player dinámicamente)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Buscar URLs de servidores comunes en strings
                matches = re.findall(r'(https?://[^\s"\']+(?:ok\.ru|dailymotion\.com|rumble\.com)[^\s"\']*)', script.string)
                embeds.extend(matches)

        return list(set(embeds))

    def get_available_qualities(self, url):
        """Intenta detectar las calidades disponibles para una URL."""
        embeds = self.find_embed_urls(url)
        # Intentar con embeds primero, luego con la URL base
        sources = embeds + [url]

        print(f"   Analizando calidades disponibles...")
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'no_warnings': True,
            'user_agent': self.session.headers['User-Agent']
        }

        all_heights = set()
        last_error = None

        for src in sources:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(src, download=False)
                    formats = info.get('formats', [])
                    for f in formats:
                        h = f.get('height')
                        if h and isinstance(h, int):
                            all_heights.add(h)
                if all_heights:
                    break
            except Exception as e:
                last_error = e
                continue

        if not all_heights:
            logger.warning(f"No se pudieron extraer calidades automáticamente: {last_error}")
            return [360, 480, 720, 1080]

        return sorted(list(all_heights), reverse=True)

    def download_episode(self, ep_data, quality=480):
        print(f"\n>>> Procesando Episodio {ep_data['number']}...")

        target_urls = [ep_data['url']]
        try:
            embeds = self.find_embed_urls(ep_data['url'])
            if embeds:
                print(f"   Servidores detectados: {len(embeds)}")
                target_urls = embeds + target_urls
        except:
            pass

        ydl_opts = {
            'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]',
            'outtmpl': f'Donghua_Ep_{ep_data["number"]}.%(ext)s',
            'noplaylist': True,
            'format_sort': [f'res:{quality}', 'ext:mp4:m4a'],
            'merge_output_format': 'mp4',
        }

        success = False
        for url in target_urls:
            print(f"   Intentando: {url}")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                success = True
                break
            except Exception as e:
                continue

        if not success:
            raise Exception(f"No se pudo descargar el episodio {ep_data['number']}. Intenta revisar el servidor manualmente.")

    def run(self):
        try:
            print("========================================")
            print("   DONGHUA DOWNLOADER PRO (TERMUX)")
            print("========================================")
            url = input("Introduce la URL del Donghua: ").strip()
            if not url: return

            seasons = self.scrape_seasons_and_episodes(url)
            if not seasons:
                print("No se detectaron temporadas.")
                return

            season_names = list(seasons.keys())
            if len(season_names) > 1:
                print("\nTemporadas encontradas:")
                for i, name in enumerate(season_names):
                    print(f"  {i+1}. {name}")

                try:
                    sel = int(input("\nSelecciona temporada (número): ")) - 1
                    if not (0 <= sel < len(season_names)):
                        print("Selección fuera de rango.")
                        return
                    selected_name = season_names[sel]
                except ValueError:
                    print("Por favor, introduce un número válido.")
                    return
            else:
                selected_name = season_names[0]
                print(f"\nTemporada: {selected_name}")

            season_info = seasons[selected_name]
            episodes = season_info['episodes']

            # Si no hay episodios pero hay URL de temporada, scrapear esa URL
            if not episodes and season_info['url'] != url:
                print(f"Cargando episodios de {selected_name}...")
                html = self.get_page_content(season_info['url'])
                episodes = self.extract_episodes(BeautifulSoup(html, 'html.parser'), season_info['url'])

            if not episodes:
                print("Error: No se encontraron episodios.")
                return

            print(f"Rango detectado: {episodes[0]['number']} - {episodes[-1]['number']}")

            try:
                start_ep = int(input(f"Episodio inicial: "))
                end_ep = int(input(f"Episodio final: "))
            except ValueError:
                print("Error: Debes introducir números para los episodios.")
                return

            to_download = [ep for ep in episodes if start_ep <= ep['number'] <= end_ep]

            if not to_download:
                print("No hay episodios en el rango seleccionado.")
                return

            qualities = self.get_available_qualities(to_download[0]['url'])
            print("\nCalidades disponibles (aproximadas):")
            for i, q in enumerate(qualities):
                print(f"  {i+1}. {q}p")

            try:
                q_idx = int(input("\nSelecciona calidad (número) [Defecto 480p]: ") or "0") - 1
                if 0 <= q_idx < len(qualities):
                    selected_quality = qualities[q_idx]
                else:
                    selected_quality = 480
            except ValueError:
                selected_quality = 480

            print(f"Calidad seleccionada: {selected_quality}p")

            for ep in to_download:
                self.download_episode(ep, quality=selected_quality)

            print("\n¡Descargas completadas!")

        except Exception as e:
            self.handle_error(e)

    def handle_error(self, e):
        error_msg = traceback.format_exc()
        print("\n" + "!"*40 + "\n ERROR DETECTADO \n" + "!"*40)
        print(f"\nMensaje: {e}\n")
        print("Análisis técnico:")
        print(error_msg)

        if input("\n¿Exportar log? (s/n): ").lower() == 's':
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(error_msg)
            print(f"Log guardado en {self.log_file}")

if __name__ == "__main__":
    downloader = DonghuaDownloader()
    downloader.run()
