#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
    DONGHUA LIFE - AUTOMATED MULTI-EPISODE DOWNLOADER v2.5.1
========================================================================
    * Fusión Magistral de v1.5.0 y v2.5
    * Scrapping Brutal con Paginación y Deep Discovery
    * Motor yt-dlp Pro + Fallbacks de CDN
    * Registro de Filtrado Magistral (JSON)
========================================================================
"""

import os
import re
import sys
import json
import time
import logging
import traceback
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urljoin
import yt_dlp

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

VERSION = "2.5.1"

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://donghualife.com/",
            "Origin": "https://donghualife.com"
        })

    def add_trace(self, url, action, reason):
        self.filtering_trace.append({
            'timestamp': time.time(),
            'url': url,
            'action': action,
            'reason': reason
        })

    def get_page_content(self, url, retries=3):
        for i in range(retries):
            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
                return response.text
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if i < retries - 1:
                    time.sleep(2)
                    continue
                raise
            except Exception as e:
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
                            if any(x in str_data for x in ['episodio', 'episode', 'seasons']):
                                found_data.append(data)
                    except:
                        continue
        return found_data

    def scrape_seasons_and_episodes(self, url, html=None, deep=True):
        if not html:
            html = self.get_page_content(url)
        soup = BeautifulSoup(html, 'html.parser')
        seasons = {}

        # Filtro maestro
        base_slug = getattr(self, 'base_slug_filter', '')
        if not base_slug:
            url_parts = url.rstrip('/').split('/')
            current_slug = url_parts[-1].replace('season-', '').replace('series-', '')
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
                            self.add_trace(s_url, "SEASON_JSON", f"Encontrada temporada: {name}")
                            seasons[name] = {'url': s_url, 'episodes': []}

        # 2. Intentar mediante Selectores CSS
        season_selectors = [
            '.seasons-container a', '.nav-tabs a', '.season-list a',
            '.temporadas a', '.season-links a', '.field--name-field-temporada a',
            '.field--name-field-series a'
        ]
        for sel in season_selectors:
            try:
                found = soup.select(sel)
                for link in found:
                    name = link.get_text(strip=True) or "Temporada"
                    href = urljoin(url, link.get('href', ''))
                    if href and href != url and ('/season/' in href or '/series/' in href) and base_slug in href:
                        if not any(s['url'] == href for s in seasons.values()):
                            self.add_trace(href, "SEASON_CSS", f"Nueva temporada: {name}")
                            seasons[name] = {'url': href, 'episodes': []}
            except: continue

        # 3. Descubrimiento Profundo
        if deep:
            series_link = soup.find('a', href=re.compile(rf'/series/{base_slug}$|/series/{base_slug}-'))
            if not series_link:
                bc = soup.select_one('.breadcrumb, .breadcrumbs')
                if bc: series_link = bc.find('a', href=re.compile(r'/series/'))

            if series_link:
                series_url = urljoin(url, series_link.get('href', ''))
                if series_url not in [s['url'] for s in seasons.values()]:
                    self.add_trace(series_url, "DEEP_DISCOVERY", "Saltando a serie principal")
                    other_seasons = self.scrape_seasons_and_episodes(series_url, deep=False)
                    seasons.update(other_seasons)

        if not seasons:
            seasons['Temporada 1'] = {'url': url, 'episodes': []}
        return seasons

    def extract_episodes(self, soup, base_url):
        episodes = []
        base_slug = getattr(self, 'base_slug_filter', '')

        main_content = soup.select_one('#main-content, .region-content, .block-system-main-block, #block-donghualife-content') \
                       or soup.find("main") or soup.find("article") or soup

        potential_links = main_content.find_all('a', href=re.compile(r'/episode/|episodio|capitulo|cap-\d+'))

        # Añadir selectores manuales
        selectors = ['.episodes-list a', '.list-episodes a', '.ep-list a', '#episode-list a', '.views-field-title a', '.views-table a']
        for sel in selectors:
            try: potential_links.extend(main_content.select(sel))
            except: continue

        for l in potential_links:
            href = l.get('href', '')
            if base_slug in href and '/series/' not in href and '/season/' not in href:
                title = l.get_text(strip=True)
                full_url = urljoin(base_url, href)
                last_part = full_url.rstrip('/').split('/')[-1]
                num_match = re.search(r'-x(\d+)', last_part) or re.search(r'(\d+)$', last_part) or re.search(r'(\d+)', title)
                num = int(num_match.group(1)) if num_match else None
                if num is not None:
                    if not any(e['number'] == num for e in episodes):
                        self.add_trace(full_url, "ACCEPT_EP", f"Ep {num} detectado")
                        episodes.append({'number': num, 'url': full_url, 'title': title})
            else:
                self.add_trace(href, "REJECT_EP", f"No coincide con slug '{base_slug}'")

        return sorted(episodes, key=lambda x: x['number'])

    def buscar_reproductor(self, html_source, ep_num):
        soup = BeautifulSoup(html_source, 'html.parser')
        embeds = []

        # 1. Tags de video HTML5
        for src in soup.find_all('source'):
            u = src.get('src')
            if u: embeds.append(u)

        # 2. Iframes
        server_patterns = ['dailymotion.com', 'ok.ru', 'rumble.com', 'voe.sx', 'vidoza.net', 'filemoon', 'streamwish']
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src:
                if any(srv in src.lower() for srv in server_patterns):
                    embeds.append('https:' + src if src.startswith('//') else src)

        # 3. Scripts JS
        for s in soup.find_all('script'):
            if s.string:
                if any(x in s.string for x in ["player", "jwplayer"]):
                    m = re.search(r'(https?://[^"\s]+\.(?:mp4|m3u8))', s.string)
                    if m: embeds.append(m.group(1).replace('\\', ''))
                matches = re.findall(r'(https?://[^\s"\']+(?:ok\.ru|dailymotion\.com|rumble\.com|filemoon)[^\s"\']*)', s.string)
                embeds.extend(matches)

        return list(set(embeds))

    def get_available_qualities(self, url):
        try:
            sources = self.buscar_reproductor(self.get_page_content(url), 0) + [url]
            print(f"   Analizando calidades disponibles...")
            all_heights = set()
            for src in sources:
                try:
                    with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                        info = ydl.extract_info(src, download=False)
                        for f in info.get('formats', []):
                            if 'timeline' in f.get('format_id', '').lower(): continue
                            h = f.get('height')
                            if h and isinstance(h, int) and h > 100: all_heights.add(h)
                    if all_heights: break
                except: continue
            return sorted(list(all_heights), reverse=True) or [360, 480, 720, 1080]
        except: return [360, 480, 720, 1080]

    def sanitize_filename(self, name):
        for word in ["Episodios", "Capítulos", "Inicio", "Donghua"]:
            name = re.sub(rf"^{word}\s*[:\-]?\s*", "", name, flags=re.IGNORECASE)
            name = re.sub(rf"\s*[:\-]?\s*{word}$", "", name, flags=re.IGNORECASE)
        sanitized = re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")
        return sanitized or "Donghua"

    def download_episode(self, ep_num, ep_data=None, quality=480, simulation=False):
        print(f"\n[*] Procesando episodio {ep_num}...")

        slug = self.series_name.lower().replace(" ", "-").replace("_", "-")
        base_slug = getattr(self, 'base_slug_filter', slug)

        # Generar pool de fuentes
        target_urls = [
            f"https://donghualife.com/episode/{base_slug}-x{ep_num}",
            f"https://donghualife.com/watch/{base_slug}-episode-{ep_num}",
        ]
        if ep_data: target_urls.append(ep_data['url'])

        final_sources = []
        for url in target_urls:
            try:
                html = self.get_page_content(url)
                final_sources.extend(self.buscar_reproductor(html, ep_num))
            except: pass
        final_sources.extend(target_urls)

        # Fallbacks CDN v2.5
        final_sources.append(f"https://cdn.donghualife.com/files/mp4/{base_slug}-episode-{ep_num}-{quality}p.mp4")
        final_sources.append(f"https://cdn.donghualife.com/video/mp4/{base_slug}-ep-{quality}p.mp4")

        if not os.path.exists(self.output_folder): os.makedirs(self.output_folder)
        filename = os.path.join(self.output_folder, f"{self.series_name}_Ep_{ep_num:03d}_{quality}p.%(ext)s")

        if simulation:
            print(f"   [SIMULACIÓN] Fuentes detectadas: {list(set(final_sources))}")
            return

        class TqdmProgress:
            def __init__(self): self.pbar = None
            def __call__(self, d):
                if d['status'] == 'downloading':
                    if self.pbar is None:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc=f"Ep {ep_num}")
                    if self.pbar: self.pbar.update(d.get('downloaded_bytes', 0) - self.pbar.n)
                elif d['status'] == 'finished' and self.pbar: self.pbar.close()

        ydl_opts = {
            'format': f'bestvideo[height<={quality}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<={quality}]/best',
            'outtmpl': filename, 'noplaylist': True, 'quiet': True, 'no_warnings': True,
            'progress_handlers': [TqdmProgress()], 'merge_output_format': 'mp4',
            'user_agent': self.session.headers['User-Agent']
        }

        unique_sources = [x for i, x in enumerate(final_sources) if x not in final_sources[:i]]
        for url in unique_sources:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                print(f"[+] Completado: Ep {ep_num}")
                return
            except:
                if ".mp4" in url:
                    try:
                        resp = self.session.get(url, stream=True, timeout=15)
                        resp.raise_for_status()
                        total = int(resp.headers.get('content-length', 0))
                        with open(filename.replace("%(ext)s", "mp4"), 'wb') as f:
                            with tqdm(total=total, unit='B', unit_scale=True, desc=f"Direct Ep {ep_num}") as pbar:
                                for chunk in resp.iter_content(1024*32):
                                    f.write(chunk); pbar.update(len(chunk))
                        return
                    except: continue
        print(f"[-] No se encontró fuente válida para el Ep {ep_num}")

    def run(self):
        try:
            print("============================================================")
            print(f"           DONGHUA DOWNLOADER PRO v{VERSION}")
            print("============================================================")
            url = input("-> Introduce la URL del Donghua: ").strip()
            if not url: return

            # Inicializar Filtro Maestro
            url_slug = url.rstrip('/').split('/')[-1].replace('season-', '').replace('series-', '')
            self.base_slug_filter = re.sub(r'-\d+$', '', url_slug)
            self.add_trace(url, "START", f"Filtro maestro: {self.base_slug_filter}")

            html = self.get_page_content(url)
            soup = BeautifulSoup(html, 'html.parser')

            # Nombre de la serie (OG -> H1 -> Breadcrumbs)
            og = soup.find("meta", property="og:title")
            if og: self.series_name = self.sanitize_filename(og["content"].split("|")[0].split("-")[0])
            if not self.series_name or self.series_name == "Donghua":
                h1 = soup.select_one('#main-content h1, h1')
                if h1: self.series_name = self.sanitize_filename(h1.get_text(strip=True))
            print(f"Serie Detectada: {self.series_name}")

            seasons = self.scrape_seasons_and_episodes(url, html=html)
            all_episodes = []

            print(f"\n[+] Escaneando serie completa para detectar todos los episodios...")
            for s_name, s_info in seasons.items():
                print(f"   Analizando {s_name}...")
                curr_url = s_info['url']
                visited = set()
                while curr_url and curr_url not in visited:
                    visited.add(curr_url)
                    pg_soup = BeautifulSoup(self.get_page_content(curr_url), 'html.parser')
                    new_eps = self.extract_episodes(pg_soup, curr_url)
                    for ne in new_eps:
                        if not any(e['number'] == ne['number'] for e in all_episodes):
                            all_episodes.append(ne)
                    next_link = pg_soup.select_one('li.pager__item--next a, li.pager-next a, a.next')
                    curr_url = urljoin(curr_url, next_link.get('href', '')) if next_link else None

            all_episodes.sort(key=lambda x: x['number'])
            ep_map = {ep['number']: ep for ep in all_episodes}
            min_e = all_episodes[0]['number'] if all_episodes else 1
            max_e = all_episodes[-1]['number'] if all_episodes else 224

            print(f"\n[!] Resumen de Escaneo:")
            print(f"-> Total episodios detectados: {len(all_episodes)}")
            print(f"-> Rango disponible: {min_e} al {max_e}")

            try:
                start_ep = int(input(f"\n-> Episodio INICIAL [1]: ") or "1")
                end_ep = int(input(f"-> Episodio FINAL [{max_e}]: ") or str(max_e))
            except: start_ep, end_ep = 1, max_e

            probe_url = ep_map[start_ep]['url'] if start_ep in ep_map else (all_episodes[0]['url'] if all_episodes else url)
            qualities = self.get_available_qualities(probe_url)
            for i, q in enumerate(qualities): print(f"  {i+1}. {q}p")
            q_idx = int(input(f"-> Selecciona calidad (1-{len(qualities)}) [480p]: ") or "0") - 1
            selected_quality = qualities[q_idx] if 0 <= q_idx < len(qualities) else 480

            sim_in = input("-> ¿Modo Simulación? (s/n) [n]: ").lower()
            simulation_mode = True if sim_in == 's' else False

            for ep_num in range(start_ep, end_ep + 1):
                self.download_episode(ep_num, ep_map.get(ep_num), selected_quality, simulation_mode)

            with open(self.magisterial_log, "w", encoding="utf-8") as f:
                json.dump({'url': url, 'episodes_found': len(all_episodes), 'trace': self.filtering_trace}, f, indent=4, ensure_ascii=False)
            print("\n[+] ¡Proceso finalizado con éxito!")

        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"\n!!! ERROR CRÍTICO !!!\n{error_msg}")
            with open(self.log_file, "w") as f: f.write(error_msg)
            with open(self.magisterial_log, "w", encoding="utf-8") as f:
                json.dump({'url': url, 'error': str(e), 'trace': self.filtering_trace}, f, indent=4, ensure_ascii=False)
            print(f"Informes guardados en {self.log_file} y {self.magisterial_log}")

if __name__ == "__main__":
    DonghuaDownloader().run()
