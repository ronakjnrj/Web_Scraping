from os import path
from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from collections import defaultdict
from django.shortcuts import HttpResponse
import re, traceback, time, json, urllib3, logging, sys, warnings
from selenium.webdriver.common.by import By
from scraping.models import Tbl_website_list
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service as FirefoxService
from ..utils import *
from ..models import Tbl_tdr_basic_details, Tbl_website_list,Tbl_recent_hmdb
from selenium.common.exceptions import JavascriptException, WebDriverException, TimeoutException
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException


BASE_DIR = Path(__file__).resolve().parent.parent
website_data = Tbl_website_list.objects.values('s_no', 'url')


Instance_name = Path.home().name
app_name = Path(__file__).parent.parent.name
Views_name = Path(__file__).stem
combine_path=[Instance_name,app_name,Views_name]
web_location = "/".join(combine_path[:min(2, len(combine_path))])

logger = setup_logger(468)
logger.info(f'scraping started of website ----- https://tender.nprocure.com/(468)')
logger.info('---'*50)

def nprocure_updates():
    set_download_folder("temp_2")

    try:
        # 🔹 STEP 1: Setup WebDriver and open site
        driver = setdriver()
        website_id, row_unique_id = website_id_by_url('https://tender.nprocure.com/', website_data, web_location)


        # 🔸 STEP 2: Load Corrigendum Page
        def load_page():
            try:
                driver.get("https://tender.nprocure.com/")
                time.sleep(2)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "tenderNo")))
            except:
                if respond := Tbl_website_tracker.objects.filter(unique_id=row_unique_id).order_by('-id').first():
                    respond.site_response = 0
                    respond.driver_quit = 1
                    respond.status = 2
                    respond.end_time = current_time()     
                    respond.save()


        # 🔹 STEP 3: Main Corrigendum Function
        def corrigendum_extractor():
            load_page()

            # dropdown_script = """ $('select[name="DataTables_Table_0_length"] option[value="150"]').val('100000').prop('selected', true).trigger('change'); return true; """
            # execute_script_with_retries(driver, dropdown_script)
            # time.sleep(12)

            # tender_ids = []
            # page_souce = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tbody"))).get_attribute("outerHTML")
            # soup = BeautifulSoup(page_souce, 'html.parser')
            # tbody = soup.find("tbody")

            # if tbody:
            #     for row in tbody.find_all("tr"):
            #         try:
            #             tds = row.find_all("td")
            #             if len(tds) < 2:
            #                 continue

            #             forms = tds[1].find_all("form")
            #             for form in forms:
            #                 a_tag = form.find("a")
            #                 style_value = a_tag.get("style", "")
            #                 normalized_style = " ".join(style_value.lower().split())

            #                 if "display:block" in normalized_style.replace(" ", ""):
            #                     tender_input = form.find("input", {"id": lambda x: x and x.startswith("tenderid_")})
            #                     if tender_input:
            #                         tender_id = tender_input.get("value")
            #                         tender_ids.append(tender_id)

            #         except Exception as e:
            #             continue

            # print("Listof Tender IDs:", tender_ids)
            # print("Total Number of Tender IDs:", len(tender_ids))
            # logger.info(f" Total Nummber of Tender IDs: {len(tender_ids)}")
            # logger.info("Listof Tender IDs:", tender_ids)

            # existing_ids = set(Tbl_tdr_basic_details.objects.filter(website_id=website_id, tender_id__in=tender_ids).values_list('tender_id', flat=True))
            existing_ids = [211193, 215485, 215900, 216038, 217585, 221386]

            session = create_requests_session(driver)
            driver.quit()

            # 🔹 STEP 6: Process each Tender ID
            for tender_id in existing_ids:

                base_dir = os.path.join(BASE_DIR, "main_docss")
                date = datetime.now()
                tender_path = f"{base_dir}/{date.year}/{date.month}/{date.day}/{tender_id}"

                detail_url = 'https://tender.nprocure.com/view-nit-amendment'

                payload = {
                    "_csrf": "token",
                    "tenderid": int(tender_id)
                }
                response = session.post(detail_url, data=payload, verify=False)

                # print("Status:", response.status_code)

                if response.status_code == 200 and response.text.strip():
                    save_corrigendum_html_file(response.text, tender_id)
                else:
                    logger.warning(f"Empty or failed response for tender_id {tender_id}")

                #----------------------------------------------------------------------------------#
                """ -------------------------- Document Download --------------------------------"""
                #----------------------------------------------------------------------------------#

                detail_url = 'https://tender.nprocure.com/view-nit-document'
                payload = {
                    "_csrf": "token",
                    "tenderid": int(tender_id)
                }
                response = session.post(detail_url, data=payload, verify=False)


                if response.status_code == 200 and response.text.strip():
                    download_documents_from_html(session, response.text, tender_path)
                else:
                    logger.warning(f"Failed to Download Documents for tender_id {tender_id}")

                #--------------------------------------------------------------------------------

                # for folder in sorted(os.listdir(source_path)):
                try:
                    tenderId = Tbl_tdr_basic_details.objects.get(tender_id=tender_id).id
                except:
                    continue

                update_data_dict = {}

                # Step 1: Extract corrigendum data from window2.html
                corrigendum_data={}
                windows = sorted([f for f in os.listdir(tender_path) if f.startswith("window") and f.endswith(".html")])
                for file in windows:
                    if "window1" in file:
                        html = open(os.path.join(tender_path, file), encoding="utf-8").read()
                        soup = BeautifulSoup(html, "html.parser")
                        tables = soup.find_all("table")
                        second_table = tables[1]
                        if not second_table:
                            continue

                        # Loop through window1 table rows
                        try:
                            rows = second_table.find_all("tr")[1:]
                            amendment_num = []
                            amendment_id = []

                            for idx, tr in enumerate(rows, start=1):
                                tds = tr.find_all("td")
                                if len(tds) >= 4:
                                    corr_id = str(idx)
                                    first_td = tds[0].text.strip()
                                    second_td = tds[1].text.strip()
                                    corr_subject = tds[2].text.replace('\u2013', '').strip()
                                    amendment_date = tds[3].text.strip()
                                    amendment_num.append(int(first_td))
                                    amendment_id.append(int(second_td))

                                    corrigendum_data[corr_id] = {
                                        "corr_subject": corr_subject,
                                        "publish_date": amendment_date,
                                    }
                        except : traceback.print_exc()

                        for num, a_id in zip(amendment_num, amendment_id):
                            detail_url = 'https://tender.nprocure.com/view-amendment-home'

                            payload = {
                                "tenderamendmentid": a_id,
                                "tempFlag": 2
                            }
                            response = session.post(detail_url, data=payload, verify=False)

                            print("Status:", response.status_code)

                            if response.status_code == 200 and response.text.strip():
                                save_corrigendum_html_file(response.text, tender_id, num)
                            else:
                                logger.warning(f"Empty or failed response for tender_id {tender_id}")

                        # Step 2: Loop through corrigendum folders
                        data_dict = defaultdict(lambda : None)
                        for subfolder in sorted(os.listdir(tender_path), 
                            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('-inf'), reverse=True):
                            if not subfolder.startswith("corrigendum_"):
                                continue
                            corr_path = os.path.join(tender_path, subfolder)
                            if not os.path.isdir(corr_path):
                                continue

                            corr_id = subfolder.split("_")[-1]

                            windows = sorted([f for f in os.listdir(corr_path) if f.startswith("window") and f.endswith(".html")])
                            for file in windows:
                                html = open(os.path.join(corr_path, file), encoding="utf-8").read()
                                soup = BeautifulSoup(html, "html.parser")

                                tables = soup.find_all('table')
                                for table in tables:
                                    rows = table.find_all('tr', class_= "readonly")
                                    for row in rows:
                                        tds = row.find_all('td')
                                        if len(tds) == 2:
                                            key = tds[0].get_text(strip=True).replace('\u00a0', '')
                                            value = tds[1].get_text(strip=True).replace('\t', '').replace('\n', '').replace('\xa0', '')
                                            data_dict[key] = value

                                document_section = soup.find("h4", string=lambda t: t and "Tender Documents" in t)
                                doc_names = {}
                                if document_section:
                                    document_table = document_section.find_next("table")
                                    index = 0 
                                    for row in document_table.find_all("tr"):
                                        tds = row.find_all("td")
                                        if len(tds) >= 2:
                                            doc_names[index] = tds[1].get_text(strip=True)
                                            index += 1

                                if corr_id in corrigendum_data:
                                    update_data_dict.setdefault(tenderId, {})
                                    update_data_dict[tenderId][corr_id] = {
                                        **corrigendum_data[corr_id],
                                        "corr_title"                : corrigendum_data[corr_id].get("corr_subject"),
                                        "corr_desc"                 : corrigendum_data[corr_id].get("corr_subject"),
                                        "published_date"            : corrigendum_data[corr_id].get("publish_date"),
                                        "doc_dict"                  : doc_names if doc_names else None,
                                        "doc_path"                  : None if not doc_names else tender_path,
                                        "bid_submission_start_dateTime"   : data_dict.get('Bid Submission Start Date'),
                                        "bid_submission_end_dateTime"     : data_dict.get('Bid Submission Closing Date'),
                                        "document_download_start_dateTime": data_dict.get('Bid Document Download Start Date'),
                                        "document_download_end_datetime"  : data_dict.get('Bid document download End Date'),
                                        "prebid_meeting_date"             : data_dict.get('Pre-Bid Meeting'),
                                    }

                            #Documnets move
                            

                        # Step 4: Insert to DB
                        if update_data_dict:
                            print("📥 Sending to corr_insertion")
                            corr_insertion(update_data_dict, website_id, tenderId, tender_id, row_unique_id)

        # 🔹 STEP 4: Call extractor
        corrigendum_extractor()


    except Exception:
        traceback.print_exc()
        Tbl_website_tracker.objects.filter(unique_id=row_unique_id).update(error_comment="Error Creating in Some Corrigendum")
    

    if entry := Tbl_website_tracker.objects.filter(website_id=468, unique_id = row_unique_id).order_by('-id').first():
        entry.driver_quit = 1
        entry.end_time = current_time()    
        entry.status = 4
        entry.save() 



def backup_nprocure_updates():
    set_download_folder("temp_2")

    try:
        # 🔹 STEP 1: Setup WebDriver and open site
        driver = setdriver()
        website_id, row_unique_id = website_id_by_url('https://tender.nprocure.com/', website_data, web_location)


        # 🔸 STEP 2: Load Corrigendum Page
        def load_page():
            try:
                driver.get("https://tender.nprocure.com/")
                time.sleep(2)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "tenderNo")))
            except:
                if respond := Tbl_website_tracker.objects.filter(unique_id=row_unique_id).order_by('-id').first():
                    respond.site_response = 0
                    respond.driver_quit = 1
                    respond.status = 2
                    respond.end_time = current_time()     
                    respond.save()


        # 🔹 STEP 3: Main Corrigendum Function
        def corrigendum_extractor():
            load_page()

            # dropdown_script = """ $('select[name="DataTables_Table_0_length"] option[value="150"]').val('100000').prop('selected', true).trigger('change'); return true; """
            # execute_script_with_retries(driver, dropdown_script)
            # time.sleep(12)

            # tender_ids = []
            # page_souce = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tbody"))).get_attribute("outerHTML")
            # soup = BeautifulSoup(page_souce, 'html.parser')
            # tbody = soup.find("tbody")

            # if tbody:
            #     for row in tbody.find_all("tr"):
            #         try:
            #             tds = row.find_all("td")
            #             if len(tds) < 2:
            #                 continue

            #             forms = tds[1].find_all("form")
            #             for form in forms:
            #                 a_tag = form.find("a")
            #                 style_value = a_tag.get("style", "")
            #                 normalized_style = " ".join(style_value.lower().split())

            #                 if "display:block" in normalized_style.replace(" ", ""):
            #                     tender_input = form.find("input", {"id": lambda x: x and x.startswith("tenderid_")})
            #                     if tender_input:
            #                         tender_id = tender_input.get("value")
            #                         tender_ids.append(tender_id)

            #         except Exception as e:
            #             continue

            # print("Listof Tender IDs:", tender_ids)
            # print("Total Number of Tender IDs:", len(tender_ids))
            # logger.info(f" Total Nummber of Tender IDs: {len(tender_ids)}")
            # logger.info("Listof Tender IDs:", tender_ids)

            # existing_ids = set(Tbl_tdr_basic_details.objects.filter(website_id=website_id, tender_id__in=tender_ids).values_list('tender_id', flat=True))
            existing_ids = [211193, 215485, 215900, 216038, 217585, 221386]

            session = create_requests_session(driver)
            driver.quit()

            # 🔹 STEP 6: Process each Tender ID
            for tender_id in existing_ids:
                detail_url = 'https://tender.nprocure.com/view-nit-amendment'

                payload = {
                    "_csrf": "token",
                    "tenderid": int(tender_id)
                }
                response = session.post(detail_url, data=payload, verify=False)

                # print("Status:", response.status_code)

                if response.status_code == 200 and response.text.strip():
                    save_corrigendum_html_file(response.text, tender_id)
                else:
                    logger.warning(f"Empty or failed response for tender_id {tender_id}")

                base_dir = os.path.join(BASE_DIR, "main_docss")
                date = datetime.now()
                source_path = f"{base_dir}/{date.year}/{date.month}/{date.day}"

                # for folder in sorted(os.listdir(source_path)):
                try:
                    tenderId = Tbl_tdr_basic_details.objects.get(tender_id=tender_id).id
                except:
                    continue
                # tender_path = os.path.join(source_path, folder)
                tender_path = os.path.join(source_path, str(tender_id))

                update_data_dict = {}

                # Step 1: Extract corrigendum data from window2.html
                corrigendum_data={}
                windows = sorted([f for f in os.listdir(tender_path) if f.startswith("window") and f.endswith(".html")])
                for file in windows:
                    if "window1" in file:
                        html = open(os.path.join(tender_path, file), encoding="utf-8").read()
                        soup = BeautifulSoup(html, "html.parser")
                        tables = soup.find_all("table")
                        second_table = tables[1]
                        if not second_table:
                            continue

                        # Loop through window1 table rows
                        try:
                            rows = second_table.find_all("tr")[1:]
                            amendment_num = []
                            amendment_id = []

                            for idx, tr in enumerate(rows, start=1):
                                tds = tr.find_all("td")
                                if len(tds) >= 4:
                                    corr_id = str(idx)
                                    first_td = tds[0].text.strip()
                                    second_td = tds[1].text.strip()
                                    corr_subject = tds[2].text.replace('\u2013', '').strip()
                                    amendment_date = tds[3].text.strip()
                                    amendment_num.append(int(first_td))
                                    amendment_id.append(int(second_td))

                                    corrigendum_data[corr_id] = {
                                        "corr_subject": corr_subject,
                                        "publish_date": amendment_date,
                                    }
                        except : traceback.print_exc()

                        for num, a_id in zip(amendment_num, amendment_id):
                            detail_url = 'https://tender.nprocure.com/view-amendment-home'

                            payload = {
                                "tenderamendmentid": a_id,
                                "tempFlag": 2
                            }
                            response = session.post(detail_url, data=payload, verify=False)

                            print("Status:", response.status_code)

                            if response.status_code == 200 and response.text.strip():
                                save_corrigendum_html_file(response.text, tender_id, num)
                            else:
                                logger.warning(f"Empty or failed response for tender_id {tender_id}")

                        # Step 2: Loop through corrigendum folders
                        data_dict = defaultdict(lambda : None)
                        for subfolder in sorted(os.listdir(tender_path), 
                            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('-inf'), reverse=True):
                            if not subfolder.startswith("corrigendum_"):
                                continue
                            corr_path = os.path.join(tender_path, subfolder)
                            if not os.path.isdir(corr_path):
                                continue

                            corr_id = subfolder.split("_")[-1]

                            windows = sorted([f for f in os.listdir(corr_path) if f.startswith("window") and f.endswith(".html")])
                            for file in windows:
                                html = open(os.path.join(corr_path, file), encoding="utf-8").read()
                                soup = BeautifulSoup(html, "html.parser")

                                tables = soup.find_all('table')
                                for table in tables:
                                    rows = table.find_all('tr', class_= "readonly")
                                    for row in rows:
                                        tds = row.find_all('td')
                                        if len(tds) == 2:
                                            key = tds[0].get_text(strip=True).replace('\u00a0', '')
                                            value = tds[1].get_text(strip=True).replace('\t', '').replace('\n', '').replace('\xa0', '')
                                            data_dict[key] = value                

                                if corr_id in corrigendum_data:
                                    update_data_dict.setdefault(tenderId, {})
                                    update_data_dict[tenderId][corr_id] = {
                                        **corrigendum_data[corr_id],
                                        "corr_title"                : corrigendum_data[corr_id].get("corr_subject"),
                                        "corr_desc"                 : corrigendum_data[corr_id].get("corr_subject"),
                                        "published_date"            : corrigendum_data[corr_id].get("publish_date"),

                                        "bid_submission_start_dateTime"   : data_dict.get('Bid Submission Start Date'),
                                        "bid_submission_end_dateTime"     : data_dict.get('Bid Submission Closing Date'),
                                        "document_download_start_dateTime": data_dict.get('Bid Document Download Start Date'),
                                        "document_download_end_datetime"  : data_dict.get('Bid document download End Date'),
                                        "prebid_meeting_date"             : data_dict.get('Pre-Bid Meeting'),
                                    }                

                        # Step 4: Insert to DB
                        if update_data_dict:
                            print("📥 Sending to corr_insertion")
                            corr_insertion(update_data_dict, website_id, tenderId, tender_id, row_unique_id)

        # 🔹 STEP 4: Call extractor
        corrigendum_extractor()


    except Exception:
        traceback.print_exc()
        Tbl_website_tracker.objects.filter(unique_id=row_unique_id).update(error_comment="Error Creating in Some Corrigendum")
    

    if entry := Tbl_website_tracker.objects.filter(website_id=468, unique_id = row_unique_id).order_by('-id').first():
        entry.driver_quit = 1
        entry.end_time = current_time()    
        entry.status = 4
        entry.save() 

