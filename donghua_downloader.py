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
import time
from tqdm import tqdm

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

VERSION = "1.4.0"

class DonghuaDownloader:
    def __init__(self):
        self.log_file = "donghua_error.log"
        self.magisterial_log = "donghua_magisterial_log.json"
        self.filtering_trace = []
        self.series_name = "Donghua"
        self.output_folder = "Donghua_Descargas"

        if cloudscraper:
            self.session = cloudscraper.create_scraper()
            logger.info("Cloudscraper activado para evadir protecciones.")
        else:
            self.session = requests.Session()

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://donghualife.com/',
            'Origin': 'https://donghualife.com'
        })

    def get_page_content(self, url, retries=3):
        for i in range(retries):
            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
                return response.text
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if i < retries - 1:
                    logger.warning(f"Reintentando {url} ({i+1}/{retries}) por error de conexión: {e}")
                    time.sleep(2)
                    continue
                logger.error(f"Error fatal al acceder a {url} después de {retries} intentos.")
                raise
            except Exception as e:
                logger.error(f"Error al acceder a {url}: {e}")
                raise

    def find_json_in_html(self, html):
        """Busca y extrae objetos JSON de etiquetas <script>."""
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script')
        found_data = []
        for script in scripts:
            if script.string:
                json_matches = re.findall(r'({[\s\S]*?}|\[[\s\S]*?\])', script.string)
                for match in json_matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, (dict, list)):
                            str_data = str(data).lower()
                            if 'episodio' in str_data or 'episode' in str_data or 'seasons' in str_data:
                                found_data.append(data)
                    except:
                        continue
        return found_data

    def scrape_seasons_and_episodes(self, url, html=None, deep=True):
        if not html:
            html = self.get_page_content(url)
        soup = BeautifulSoup(html, 'html.parser')

        seasons = {}

        # Slug de la serie actual para filtrar
        url_parts = url.rstrip('/').split('/')
        last_part = url_parts[-1]
        current_slug = last_part.replace('season-', '').replace('series-', '')
        base_slug = re.sub(r'-\d+$', '', current_slug)

        # 1. Intentar mediante JSON
        json_data_list = self.find_json_in_html(html)
        for data in json_data_list:
            if isinstance(data, dict):
                if 'seasons' in data and isinstance(data['seasons'], list):
                    for i, s in enumerate(data['seasons']):
                        name = s.get('name', f"Temporada {i+1}")
                        s_url = urljoin(url, s.get('url', ''))
                        if base_slug in s_url:
                            seasons[name] = {'url': s_url, 'episodes': []}
                elif 'episodes' in data and isinstance(data['episodes'], list):
                    if 'Temporada 1' not in seasons:
                        seasons['Temporada 1'] = {'url': url, 'episodes': []}
                    for ep in data['episodes']:
                        num = ep.get('number') or ep.get('episode_number')
                        e_url = urljoin(url, ep.get('url', ep.get('link', '')))
                        if num and e_url and base_slug in e_url:
                            seasons['Temporada 1']['episodes'].append({
                                'number': int(num),
                                'url': e_url,
                                'title': ep.get('title', f"Episodio {num}")
                            })

        # 2. Intentar mediante Selectores CSS
        season_selectors = [
            '.seasons-container a',
            '.nav-tabs a',
            '.season-list a',
            '.temporadas a',
            '.season-links a',
            '.field--name-field-temporada a',
            '.field--name-field-series a'
        ]

        season_links = []
        for sel in season_selectors:
            try:
                found = soup.select(sel)
                if found:
                    season_links.extend(found)
            except:
                continue

        for i, link in enumerate(season_links):
            name = link.get_text(strip=True) or f"Temporada {i+1}"
            href = urljoin(url, link.get('href', ''))
            # Filtro estricto: la URL debe contener el slug base
            if href and href != url and ('/season/' in href or '/series/' in href) and base_slug in href:
                if not any(s['url'] == href for s in seasons.values()):
                    seasons[name] = {'url': href, 'episodes': []}

        # 3. Descubrimiento Profundo: Si es una página de temporada, buscar la página de la serie
        if deep:
            series_link = soup.find('a', href=re.compile(rf'/series/{base_slug}$|/series/{base_slug}-'))
            if series_link:
                series_url = urljoin(url, series_link.get('href', ''))
                if series_url not in [s['url'] for s in seasons.values()]:
                    logger.info(f"Descubierta serie principal: {series_url}")
                    other_seasons = self.scrape_seasons_and_episodes(series_url, deep=False)
                    seasons.update(other_seasons)

        if not seasons:
            seasons['Temporada 1'] = {'url': url, 'episodes': self.extract_episodes(soup, url)}

        return seasons

    def add_trace(self, url, action, reason):
        self.filtering_trace.append({
            'timestamp': time.time(),
            'url': url,
            'action': action,
            'reason': reason
        })

    def extract_episodes(self, soup, base_url):
        episodes = []

        # Usar el filtro maestro definido en run()
        base_slug = getattr(self, 'base_slug_filter', '')

        # Traza de configuración de filtrado
        self.add_trace(base_url, "CONFIG", f"Filtro base: {base_slug}")

        main_content = soup.select_one('#main-content, .region-content, .block-system-main-block, #block-donghualife-content') \
                       or soup.find("main") or soup.find("article") or soup

        potential_links = main_content.find_all('a', href=re.compile(r'/episode/|episodio|capitulo'))

        links = []
        for l in potential_links:
            href = l.get('href', '')

            # Análisis detallado para el log magistral
            if '/series/' in href or '/season/' in href:
                self.add_trace(href, "REJECT", "Es un link de serie o temporada")
                continue

            if base_slug not in href:
                self.add_trace(href, "REJECT", f"No coincide con slug maestro '{base_slug}'")
                continue

            if l not in links:
                self.add_trace(href, "ACCEPT", "Coincide con filtros de episodio")
                links.append(l)

        selectors = [
            '.episodes-list a', '.list-episodes a', '.ep-list a',
            '#episode-list a', '.item-episode a', '.views-field-title a',
            '.views-table a'
        ]
        for sel in selectors:
            try:
                found_links = main_content.select(sel)
                for fl in found_links:
                    href = fl.get('href', '')
                    if base_slug in href and '/series/' not in href and '/season/' not in href:
                        if fl not in links:
                            links.append(fl)
            except:
                continue

        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href')
            if href:
                href = urljoin(base_url, href)
                url_parts = href.rstrip('/').split('/')
                last_part = url_parts[-1]

                num_match = re.search(r'-x(\d+)', last_part) or \
                            re.search(r'capitulo-(\d+)', last_part) or \
                            re.search(r'episodio-(\d+)', last_part) or \
                            re.search(r'-(\d+)$', last_part) or \
                            re.search(r'(\d+)', title)

                num = int(num_match.group(1)) if num_match else None
                if num is not None:
                    episodes.append({'number': num, 'url': href, 'title': title})

        unique_eps = {}
        for ep in episodes:
            if ep['number'] not in unique_eps:
                unique_eps[ep['number']] = ep

        return sorted(unique_eps.values(), key=lambda x: x['number'])

    def find_embed_urls(self, ep_url, html=None):
        if not html:
            try: html = self.get_page_content(ep_url)
            except: return []
        soup = BeautifulSoup(html, 'html.parser')
        embeds = []

        sources = soup.find_all('source')
        for src in sources:
            s_url = src.get('src')
            if s_url: embeds.append(urljoin(ep_url, s_url))

        server_patterns = [
            'dailymotion.com', 'ok.ru', 'rumble.com', 'voe.sx', 'vidoza.net',
            'filemoon', 'streamwish', 'vidhide', 'filelions', 'streamtape',
            'mp4upload', 'doodstream', 'mixdrop'
        ]

        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src:
                if any(srv in src.lower() for srv in server_patterns):
                    if src.startswith('//'): src = 'https:' + src
                    embeds.append(src)

        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                if any(x in script.string for x in ["var player", "player", "jwplayer"]):
                    m = re.search(r'(https?://[^"\s]+\.(?:mp4|m3u8))', script.string)
                    if m: embeds.append(m.group(1).replace('\\', ''))

                pattern = r'(https?://[^\s"\']+(?:' + '|'.join(server_patterns).replace('.', r'\.') + r')[^\s"\']*)'
                matches = re.findall(pattern, script.string, re.IGNORECASE)
                embeds.extend(matches)

        return list(set(embeds))

    def get_available_qualities(self, url):
        """Detecta calidades disponibles."""
        embeds = self.find_embed_urls(url)
        sources = embeds + [url]

        print(f"   Analizando calidades disponibles en los servidores...")
        ydl_opts = {
            'quiet': True, 'noplaylist': True, 'no_warnings': True,
            'user_agent': self.session.headers['User-Agent'],
            'check_formats': True
        }

        all_heights = set()
        for src in sources:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(src, download=False)
                    formats = info.get('formats', [])
                    for f in formats:
                        if 'timeline' in f.get('format_id', '').lower() or 'storyboard' in f.get('format_id', '').lower():
                            continue
                        h = f.get('height')
                        if h and isinstance(h, int) and h > 100:
                            all_heights.add(h)
                if all_heights: break
            except: continue

        if not all_heights: return [360, 480, 720, 1080]
        return sorted(list(all_heights), reverse=True)

    def sanitize_filename(self, name):
        """Limpia el nombre para que sea un nombre de archivo válido."""
        for word in ["Episodios", "Capítulos", "Inicio", "Donghua"]:
            name = re.sub(rf"^{word}\s*[:\-]?\s*", "", name, flags=re.IGNORECASE)
            name = re.sub(rf"\s*[:\-]?\s*{word}$", "", name, flags=re.IGNORECASE)

        sanitized = re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")
        return sanitized or "Donghua"

    def download_episode(self, ep_data, quality=480, simulation=False):
        print(f"\n>>> Preparando Episodio {ep_data['number']}...")

        target_urls = []
        slug = self.series_name.lower().replace(" ", "-").replace("_", "-")
        target_urls.append(f"https://donghualife.com/watch/{slug}-episode-{ep_data['number']}")
        target_urls.append(ep_data['url'])

        final_sources = []
        for url in target_urls:
            if "watch/" in url or "/episode/" in url:
                embeds = self.find_embed_urls(url)
                final_sources.extend(embeds)
        final_sources.extend(target_urls)
        final_sources.append(f"https://cdn.donghualife.com/files/mp4/{slug}-episode-{ep_data['number']}-{quality}p.mp4")

        if not os.path.exists(self.output_folder): os.makedirs(self.output_folder)
        safe_name = self.series_name.replace(" ", "_")
        filename = os.path.join(self.output_folder, f"{safe_name}_Ep_{ep_data['number']}.%(ext)s")

        class TqdmProgress:
            def __init__(self): self.pbar = None
            def __call__(self, d):
                if d['status'] == 'downloading':
                    if self.pbar is None:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc=f"Ep {ep_data['number']}")
                    self.pbar.update(d.get('downloaded_bytes', 0) - self.pbar.n)
                elif d['status'] == 'finished':
                    if self.pbar: self.pbar.close()

        ydl_opts = {
            'format': f'bestvideo[height<={quality}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<={quality}]/best',
            'outtmpl': filename, 'noplaylist': True,
            'format_sort': [f'res:{quality}', 'vcodec:h264', 'ext:mp4:m4a'],
            'merge_output_format': 'mp4', 'user_agent': self.session.headers['User-Agent'],
            'no_warnings': True, 'quiet': True, 'progress_handlers': [TqdmProgress()],
        }

        if simulation:
            print(f"   [SIMULACIÓN] Fuentes: {list(set(final_sources))}")
            return

        seen = set()
        unique_sources = [x for x in final_sources if not (x in seen or seen.add(x))]

        for url in unique_sources:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                return
            except:
                if ".mp4" in url:
                    try:
                        resp = self.session.get(url, stream=True, timeout=15)
                        resp.raise_for_status()
                        total = int(resp.headers.get('content-length', 0))
                        with open(filename.replace("%(ext)s", "mp4"), 'wb') as f:
                            with tqdm(total=total, unit='B', unit_scale=True, desc=f"Direct Ep {ep_data['number']}") as pbar:
                                for chunk in resp.iter_content(1024*32):
                                    f.write(chunk)
                                    pbar.update(len(chunk))
                        return
                    except: continue
        logger.error(f"Fallo descarga Ep {ep_data['number']}")

    def run(self):
        try:
            print(f"========================================")
            print(f"   DONGHUA DOWNLOADER PRO v{VERSION}")
            print(f"========================================")
            url = input("Introduce la URL del Donghua: ").strip()
            if not url: return

            # Extraer slug base de la URL principal de entrada
            url_slug = url.rstrip('/').split('/')[-1].replace('season-', '').replace('series-', '')
            self.base_slug_filter = re.sub(r'-\d+$', '', url_slug)
            logger.info(f"Filtro maestro activado para: {self.base_slug_filter}")

            html = self.get_page_content(url)
            soup = BeautifulSoup(html, 'html.parser')

            h1 = soup.select_one('#main-content h1, h1.page-title, #block-donghualife-page-title h1, h1')
            if h1: self.series_name = self.sanitize_filename(h1.get_text(strip=True))

            if not self.series_name or self.series_name == "Donghua":
                breadcrumb = soup.select_one('.breadcrumb, .breadcrumbs')
                if breadcrumb:
                    links = breadcrumb.find_all('a')
                    for link in reversed(links):
                        text = link.get_text(strip=True)
                        if text and text.lower() not in ["inicio", "donghuas", "episodios"]:
                            self.series_name = self.sanitize_filename(text)
                            break

            print(f"Serie: {self.series_name}")
            seasons = self.scrape_seasons_and_episodes(url, html=html)

            print(f"\n[+] Escaneando toda la serie para encontrar todos los episodios...")
            all_episodes = []

            for s_name, s_info in seasons.items():
                print(f"   Analizando {s_name}...")
                current_url = s_info['url']
                visited_urls = set()
                while current_url and current_url not in visited_urls:
                    visited_urls.add(current_url)
                    pg_html = self.get_page_content(current_url)
                    pg_soup = BeautifulSoup(pg_html, 'html.parser')
                    new_eps = self.extract_episodes(pg_soup, current_url)
                    for ne in new_eps:
                        if not any(e['number'] == ne['number'] for e in all_episodes):
                            all_episodes.append(ne)
                    next_link = pg_soup.select_one('li.pager__item--next a, li.pager-next a, .pagination a[rel="next"], a.next')
                    current_url = urljoin(current_url, next_link.get('href', '')) if next_link else None

            all_episodes.sort(key=lambda x: x['number'])
            if not all_episodes:
                print("\n[!] ERROR MAGISTRAL: No se detectaron episodios.")
                print(f"Revisa '{self.magisterial_log}' para ver el rastro de filtrado.")
                with open(self.magisterial_log, "w", encoding="utf-8") as f:
                    json.dump({
                        'url_inicial': url,
                        'slug_maestro': self.base_slug_filter,
                        'trace': self.filtering_trace
                    }, f, indent=4, ensure_ascii=False)
                return

            min_ep, max_ep = all_episodes[0]['number'], all_episodes[-1]['number']
            print(f"\nTotal episodios detectados: {len(all_episodes)}")
            print(f"Rango disponible: {min_ep} al {max_ep}")

            try:
                start_ep = int(input(f"Episodio inicial [1]: ") or "1")
                end_ep = int(input(f"Episodio final [{max_ep}]: ") or str(max_ep))
            except: start_ep, end_ep = 1, max_ep

            to_download = [ep for ep in all_episodes if start_ep <= ep['number'] <= end_ep]

            if not to_download:
                print("\n[!] El rango no contiene episodios.")
                report = {'series': self.series_name, 'episodes': all_episodes}
                with open("donghua_pro_analysis.json", "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=4, ensure_ascii=False)
                return

            qualities = self.get_available_qualities(to_download[0]['url'])
            print("\nCalidades disponibles:")
            for i, q in enumerate(qualities): print(f"  {i+1}. {q}p")

            try:
                q_idx = int(input(f"\nSelecciona calidad (1-{len(qualities)}) [480p]: ") or "0") - 1
                selected_quality = qualities[q_idx] if 0 <= q_idx < len(qualities) else 480
            except: selected_quality = 480

            print(f"Calidad: {selected_quality}p\n")
            sim_in = input("¿Modo Simulación? (s/n) [n]: ").lower()
            simulation_mode = True if sim_in == 's' else False

            for ep in to_download:
                self.download_episode(ep, quality=selected_quality, simulation=simulation_mode)
            print("\n¡Todo listo!")

        except Exception as e:
            self.handle_error(e)

    def handle_error(self, e):
        error_msg = traceback.format_exc()
        print(f"\n!!! ERROR v{VERSION} !!!\n{error_msg}")
        if input("\n¿Exportar log? (s/n): ").lower() == 's':
            with open(self.log_file, "w") as f: f.write(error_msg)
            print(f"Log: {self.log_file}")

if __name__ == "__main__":
    DonghuaDownloader().run()
