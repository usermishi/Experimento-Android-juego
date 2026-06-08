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

VERSION = "1.2.5"

class DonghuaDownloader:
    def __init__(self):
        self.log_file = "donghua_error.log"
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
                    import time
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
                # Buscar patrones que parezcan JSON
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

        # 1. Intentar mediante JSON
        json_data_list = self.find_json_in_html(html)
        for data in json_data_list:
            if isinstance(data, dict):
                if 'seasons' in data and isinstance(data['seasons'], list):
                    for i, s in enumerate(data['seasons']):
                        name = s.get('name', f"Temporada {i+1}")
                        s_url = urljoin(url, s.get('url', ''))
                        seasons[name] = {'url': s_url, 'episodes': []}
                elif 'episodes' in data and isinstance(data['episodes'], list):
                    if 'Temporada 1' not in seasons:
                        seasons['Temporada 1'] = {'url': url, 'episodes': []}
                    for ep in data['episodes']:
                        num = ep.get('number') or ep.get('episode_number')
                        e_url = urljoin(url, ep.get('url', ep.get('link', '')))
                        if num and e_url:
                            seasons['Temporada 1']['episodes'].append({
                                'number': int(num),
                                'url': e_url,
                                'title': ep.get('title', f"Episodio {num}")
                            })

        if seasons and any(s['episodes'] for s in seasons.values()):
            return seasons

        # 2. Intentar mediante Selectores CSS
        season_selectors = [
            '.seasons-container a',
            '.nav-tabs a',
            '.season-list a',
            '.temporadas a',
            '.season-links a',
            '.field--name-field-temporada a',
            '.field--name-field-series a',
            'a[href*="/series/"]', # Enlaces a la serie principal
            'a[href*="/season/"]'  # Otros enlaces de temporadas
        ]

        season_links = []
        for sel in season_selectors:
            try:
                found = soup.select(sel)
                if found:
                    season_links.extend(found)
            except Exception:
                continue

        if not season_links:
            seasons['Temporada 1'] = {'url': url, 'episodes': self.extract_episodes(soup, url)}
        else:
            for i, link in enumerate(season_links):
                name = link.get_text(strip=True) or f"Temporada {i+1}"
                href = urljoin(url, link.get('href', ''))
                if href and href != url and ('/season/' in href or '/series/' in href):
                    # Evitar duplicados por URL
                    if not any(s['url'] == href for s in seasons.values()):
                        seasons[name] = {'url': href, 'episodes': []}

            # 3. Descubrimiento Profundo: Si es una página de temporada, buscar la página de la serie
            if deep:
                series_link = soup.select_one('a[href*="/series/"]')
                if series_link:
                    series_url = urljoin(url, series_link.get('href', ''))
                    if series_url not in [s['url'] for s in seasons.values()]:
                        logger.info(f"Descubierta serie principal: {series_url}")
                        other_seasons = self.scrape_seasons_and_episodes(series_url, deep=False)
                        seasons.update(other_seasons)

            if not seasons:
                seasons['Temporada 1'] = {'url': url, 'episodes': self.extract_episodes(soup, url)}

        return seasons

    def extract_episodes(self, soup, base_url):
        episodes = []

        # Slug de la serie actual para filtrar (ej: wan-jie-du-zun-2)
        url_parts = base_url.rstrip('/').split('/')
        current_slug = url_parts[-1].replace('season-', '').replace('series-', '')

        # Intentar limitar la búsqueda al contenido principal
        # Se añaden selectores más específicos para Drupal (donghualife)
        main_content = soup.select_one('#main-content, .region-content, .block-system-main-block, #block-donghualife-content') \
                       or soup.find("main") or soup.find("article") or soup

        # Buscar enlaces de episodios
        potential_links = main_content.find_all('a', href=re.compile(r'/episode/|episodio|capitulo'))

        links = []
        # Normalizar el slug para una comparación más flexible (ej: wan-jie-du-zun)
        base_slug = re.sub(r'-\d+$', '', current_slug)

        for l in potential_links:
            href = l.get('href', '')
            # Filtro: debe contener el slug base o el slug completo
            # También permitimos links que contengan el nombre de la serie sin el prefijo /episode/
            # siempre y cuando estemos en el bloque de contenido principal.
            if (base_slug in href or current_slug in href) and '/series/' not in href and '/season/' not in href:
                if l not in links:
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
                    if (base_slug in href or current_slug in href) and '/series/' not in href and '/season/' not in href:
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
            try:
                html = self.get_page_content(ep_url)
            except:
                return []
        soup = BeautifulSoup(html, 'html.parser')
        embeds = []

        # 1. Buscar en etiquetas <source> (Direct MP4/M3U8)
        sources = soup.find_all('source')
        for src in sources:
            s_url = src.get('src')
            if s_url:
                embeds.append(urljoin(ep_url, s_url))

        # 2. Servidores comunes a buscar
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
                # 3. Buscar variables de reproductor (v2.5 heuristics)
                if any(x in script.string for x in ["var player", "player", "jwplayer"]):
                    # Regex mejorado de v2.5
                    m = re.search(r'(https?://[^"\s]+\.(?:mp4|m3u8))', script.string)
                    if m: embeds.append(m.group(1).replace('\\', ''))

                # Regex más amplia para capturar URLs de servidores
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
                        # Filtrar formatos auxiliares como timeline/storyboard de Rumble
                        if 'timeline' in f.get('format_id', '').lower() or 'storyboard' in f.get('format_id', '').lower():
                            continue
                        h = f.get('height')
                        if h and isinstance(h, int) and h > 100:
                            all_heights.add(h)
                if all_heights: break
            except:
                continue

        if not all_heights:
            return [360, 480, 720, 1080]

        return sorted(list(all_heights), reverse=True)

    def sanitize_filename(self, name):
        """Limpia el nombre para que sea un nombre de archivo válido."""
        # Eliminar palabras genéricas comunes pero preservar números de temporada
        for word in ["Episodios", "Capítulos", "Inicio", "Donghua"]:
            name = re.sub(rf"^{word}\s*[:\-]?\s*", "", name, flags=re.IGNORECASE)
            name = re.sub(rf"\s*[:\-]?\s*{word}$", "", name, flags=re.IGNORECASE)

        sanitized = re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")
        return sanitized or "Donghua"

    def download_episode(self, ep_data, quality=480, simulation=False):
        print(f"\n>>> Preparando Episodio {ep_data['number']}...")

        target_urls = []

        # 1. Intentar con URL de la página de reproducción (watch pattern)
        slug = self.series_name.lower().replace(" ", "-").replace("_", "-")
        watch_url = f"https://donghualife.com/watch/{slug}-episode-{ep_data['number']}"
        target_urls.append(watch_url)

        # 2. Intentar con URL original detectada
        target_urls.append(ep_data['url'])

        # 3. Descubrir embeds de las fuentes primarias
        final_sources = []
        for url in target_urls:
            if "watch/" in url or "/episode/" in url:
                embeds = self.find_embed_urls(url)
                final_sources.extend(embeds)

        final_sources.extend(target_urls)

        # 4. Fallback CDN (v2.5 heuristic)
        cdn_fallback = f"https://cdn.donghualife.com/files/mp4/{slug}-episode-{ep_data['number']}-{quality}p.mp4"
        final_sources.append(cdn_fallback)

        # Carpeta de salida
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # Usar el nombre de la serie en el archivo
        safe_name = self.series_name.replace(" ", "_")
        filename = os.path.join(self.output_folder, f"{safe_name}_Ep_{ep_data['number']}.%(ext)s")

        class TqdmProgress:
            def __init__(self):
                self.pbar = None
            def __call__(self, d):
                if d['status'] == 'downloading':
                    if self.pbar is None:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc=f"Ep {ep_data['number']}")
                    self.pbar.update(d.get('downloaded_bytes', 0) - self.pbar.n)
                elif d['status'] == 'finished':
                    if self.pbar:
                        self.pbar.close()

        ydl_opts = {
            'format': f'bestvideo[height<={quality}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<={quality}]/best',
            'outtmpl': filename,
            'noplaylist': True,
            'format_sort': [f'res:{quality}', 'vcodec:h264', 'ext:mp4:m4a'],
            'merge_output_format': 'mp4',
            'user_agent': self.session.headers['User-Agent'],
            'no_warnings': True,
            'quiet': True,
            'progress_handlers': [TqdmProgress()],
        }

        if simulation:
            print(f"   [SIMULACIÓN] Probando fuentes para Ep {ep_data['number']}...")
            for s in list(set(final_sources)):
                print(f"   [SIMULACIÓN] Fuente detectada: {s}")
            print(f"   [SIMULACIÓN] ¡{filename} marcado como completado!")
            return

        success = False
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_sources = [x for x in final_sources if not (x in seen or seen.add(x))]

        for url in unique_sources:
            try:
                # Intento con yt-dlp
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                success = True
                break
            except:
                # Si es un link directo mp4/m3u8, intentar descarga manual con requests
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
                        success = True
                        break
                    except:
                        continue
                continue

        if not success:
            print(f"   [!] No se pudo descargar el episodio {ep_data['number']}.")

    def run(self):
        try:
            print(f"========================================")
            print(f"   DONGHUA DOWNLOADER PRO v{VERSION}")
            print(f"========================================")
            url = input("Introduce la URL del Donghua: ").strip()
            if not url: return

            html = self.get_page_content(url)
            soup = BeautifulSoup(html, 'html.parser')

            # Intentar extraer el nombre de la serie
            # Buscar en breadcrumbs o títulos específicos primero
            # Preferir el H1 primero, ya que suele incluir el nombre completo con temporada
            h1 = soup.select_one('#main-content h1, h1.page-title, #block-donghualife-page-title h1, h1')
            if h1:
                self.series_name = self.sanitize_filename(h1.get_text(strip=True))

            if not self.series_name or self.series_name == "Donghua":
                breadcrumb = soup.select_one('.breadcrumb, .breadcrumbs')
                if breadcrumb:
                    links = breadcrumb.find_all('a')
                    if len(links) >= 2:
                        for link in reversed(links):
                            text = link.get_text(strip=True)
                            if text and text.lower() not in ["inicio", "donghuas", "episodios"]:
                                self.series_name = self.sanitize_filename(text)
                                break

            if not self.series_name or self.series_name == "Donghua":
                # En donghualife, el H1 suele estar dentro del bloque principal
                h1 = soup.select_one('#main-content h1, h1.page-title, #block-donghualife-page-title h1, h1')
                if h1:
                    self.series_name = self.sanitize_filename(h1.get_text(strip=True))

            if not self.series_name or self.series_name == "Donghua":
                title_tag = soup.find('title')
                if title_tag:
                    raw_title = title_tag.get_text(strip=True).split('|')[0].split('-')[0]
                    self.series_name = self.sanitize_filename(raw_title)

            print(f"Serie: {self.series_name}")

            seasons = self.scrape_seasons_and_episodes(url, html=html)
            if not seasons:
                print("No se detectaron temporadas ni episodios.")
                return

            season_names = list(seasons.keys())
            if len(season_names) > 1:
                print("\nTemporadas encontradas:")
                for i, name in enumerate(season_names):
                    print(f"  {i+1}. {name}")

                try:
                    sel_in = input(f"\nSelecciona temporada (1-{len(season_names)}) [1]: ").strip()
                    sel = int(sel_in) - 1 if sel_in else 0
                    selected_name = season_names[sel] if 0 <= sel < len(season_names) else season_names[0]
                except:
                    selected_name = season_names[0]
            else:
                selected_name = season_names[0]
                print(f"\nTemporada detectada: {selected_name}")

            season_info = seasons[selected_name]
            episodes = season_info.get('episodes', [])

            # Siempre intentar rastrear todas las páginas para asegurar la lista completa
            print(f"Cargando lista completa de episodios (esto puede tardar si hay paginación)...")
            current_url = season_info['url']
            visited_urls = set()
            page_num = 1

            while current_url and current_url not in visited_urls:
                print(f"   Escaneando página {page_num}...")
                visited_urls.add(current_url)
                pg_html = self.get_page_content(current_url)
                pg_soup = BeautifulSoup(pg_html, 'html.parser')

                new_eps = self.extract_episodes(pg_soup, current_url)
                # Evitar duplicados
                for ne in new_eps:
                    if not any(e['number'] == ne['number'] for e in episodes):
                        episodes.append(ne)

                # Buscar link a "Siguiente" o "Página X"
                next_link = pg_soup.select_one('li.pager__item--next a, li.pager-next a, .pagination a[rel="next"], a.next, .pager-next a')
                if next_link:
                    current_url = urljoin(current_url, next_link.get('href', ''))
                    page_num += 1
                else:
                    current_url = None

                episodes.sort(key=lambda x: x['number'])

            if not episodes:
                print("Error: No se encontraron episodios en esta sección.")
                return

            # Asegurar que el rango mostrado sea amigable
            min_ep = min(e['number'] for e in episodes)
            max_ep = max(e['number'] for e in episodes)

            print(f"Episodios encontrados: {len(episodes)}")
            print(f"Rango disponible: {min_ep} al {max_ep}")

            try:
                start_ep = int(input(f"Episodio inicial [1]: ") or "1")
                end_ep = int(input(f"Episodio final [{max_ep}]: ") or str(max_ep))
            except:
                start_ep, end_ep = 1, max_ep

            to_download = [ep for ep in episodes if start_ep <= ep['number'] <= end_ep]

            # MODO BRUTAL: Si faltan episodios, buscar en todas las temporadas detectadas
            if len(to_download) < (end_ep - start_ep + 1):
                print("\n[!] Activando ESCANEO BRUTAL para encontrar episodios faltantes...")
                for s_name in season_names:
                    if s_name == selected_name and len(visited_urls) > 1: continue # Ya escaneada

                    print(f"   Analizando {s_name}...")
                    s_url = seasons[s_name]['url']
                    s_visited = set()
                    curr_s_url = s_url

                    while curr_s_url and curr_s_url not in s_visited:
                        s_visited.add(curr_s_url)
                        # Evitar re-escanear si ya lo hicimos en el loop principal
                        if curr_s_url in visited_urls and s_name == selected_name:
                             # Buscar siguiente y continuar
                             pg_html = self.get_page_content(curr_s_url)
                        else:
                             pg_html = self.get_page_content(curr_s_url)
                             pg_soup = BeautifulSoup(pg_html, 'html.parser')
                             new_eps = self.extract_episodes(pg_soup, curr_s_url)
                             for ne in new_eps:
                                 if not any(e['number'] == ne['number'] for e in episodes):
                                     episodes.append(ne)

                        pg_soup = BeautifulSoup(pg_html, 'html.parser')
                        next_link = pg_soup.select_one('li.pager__item--next a, li.pager-next a, .pagination a[rel="next"], a.next')
                        curr_s_url = urljoin(curr_s_url, next_link.get('href', '')) if next_link else None

                episodes.sort(key=lambda x: x['number'])
                to_download = [ep for ep in episodes if start_ep <= ep['number'] <= end_ep]

            # Diagnóstico final
            if len(to_download) < (end_ep - start_ep + 1):
                missing = [n for n in range(start_ep, end_ep + 1) if not any(e['number'] == n for e in episodes)]
                if missing:
                    print("\n--- DIAGNÓSTICO DE EPISODIOS FALTANTES ---")
                    print(f"Episodios totales detectados: {len(episodes)}")
                    print(f"Episodios no encontrados: {missing}")

            if not to_download:
                print("\n[!] El rango seleccionado no contiene episodios detectables.")
                print("Revisa 'donghua_discovery_report.json' para un análisis detallado.")
                report = {
                    'series': self.series_name,
                    'total_episodes_found': len(episodes),
                    'requested_range': [start_ep, end_ep],
                    'found_range': [min_ep, max_ep] if episodes else [0,0],
                    'detected_seasons': season_names,
                    'all_detected_episodes': episodes,
                    'cause': "Los episodios solicitados no están en ninguna de las temporadas detectadas automáticamente."
                }
                with open("donghua_discovery_report.json", "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=4, ensure_ascii=False)
                return

            # Opción de exportar JSON para revisión
            with open("donghua_detected.json", "w", encoding="utf-8") as f:
                json.dump({'series': self.series_name, 'episodes_to_download': to_download, 'all_available': episodes}, f, indent=4, ensure_ascii=False)

            print(f"\n[+] Se ha generado 'donghua_detected.json' con {len(to_download)} episodios.")
            input("Presiona Enter para continuar con la descarga o Ctrl+C para cancelar y revisar el JSON...")

            qualities = self.get_available_qualities(to_download[0]['url'])
            print("\nCalidades disponibles detectadas:")
            for i, q in enumerate(qualities):
                print(f"  {i+1}. {q}p")

            try:
                q_in = input(f"\nSelecciona calidad (1-{len(qualities)}) [480p]: ").strip()
                q_idx = int(q_in) - 1 if q_in else -1
                selected_quality = qualities[q_idx] if 0 <= q_idx < len(qualities) else 480
            except:
                selected_quality = 480

            print(f"Calidad elegida: {selected_quality}p\n")

            sim_in = input("¿Deseas activar el MODO SIMULACIÓN (solo descubrir links)? (s/n) [n]: ").lower()
            simulation_mode = True if sim_in == 's' else False

            for ep in to_download:
                self.download_episode(ep, quality=selected_quality, simulation=simulation_mode)

            print("\n¡Todo el proceso ha finalizado correctamente!")

        except Exception as e:
            self.handle_error(e)

    def handle_error(self, e):
        error_msg = traceback.format_exc()
        print(f"\n" + "!"*40 + f"\n ERROR CRÍTICO v{VERSION}\n" + "!"*40)
        print(f"\nMensaje: {e}\n")
        print("Detalles del error:")
        print(error_msg)
        if input("\n¿Deseas guardar el log de error en 'donghua_error.log'? (s/n): ").lower() == 's':
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(f"VERSION: {VERSION}\n")
                f.write(error_msg)
            print(f"Log exportado a: {os.path.abspath(self.log_file)}")

if __name__ == "__main__":
    DonghuaDownloader().run()
