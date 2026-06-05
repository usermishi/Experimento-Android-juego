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

        # Intentar extraer mediante JSON primero
        json_data_list = self.find_json_in_html(html)
        if json_data_list:
            logger.info("Se detectaron datos JSON en la página. Intentando procesar...")
            # Aquí se podría implementar una lógica más específica si se conoce el formato
            # Por ahora, seguimos con el scraping de HTML como respaldo robusto

        seasons = {}
        # Buscar contenedores de temporadas con enlaces
        season_links = soup.select('.seasons-container a, .nav-tabs a, .season-list a, . temporadas a')

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
        links = soup.find_all('a', href=re.compile(r'episodio|episode|capitulo|cap-\d+'))

        # Añadir links de contenedores comunes
        for selector in ['.episodes-list', '.list-episodes', '.ep-list', '#episode-list', '.item-episode']:
            links.extend(soup.select(f"{selector} a"))

        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href')
            if href:
                href = urljoin(base_url, href)
                # Extraer número de episodio
                num_match = re.search(r'(\d+)', title) or re.search(r'(\d+)', href.rstrip('/').split('/')[-1])
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

    def download_episode(self, ep_data):
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
            'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            'outtmpl': f'Donghua_Ep_{ep_data["number"]}.%(ext)s',
            'noplaylist': True,
            'format_sort': ['res:480', 'ext:mp4:m4a'],
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
                sel = int(input("\nSelecciona temporada: ")) - 1
                selected_name = season_names[sel]
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

            start_ep = int(input(f"Episodio inicial: "))
            end_ep = int(input(f"Episodio final: "))

            to_download = [ep for ep in episodes if start_ep <= ep['number'] <= end_ep]

            for ep in to_download:
                self.download_episode(ep)

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
