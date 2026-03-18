from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # ← 이거 추가
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import shutil
import glob
import os
import schedule


SAP_URL = "https://dspwp.sap.daewoong.com/sap/bc/ui2/flp?sap-client=100"
SAP_ID = "2240410"
SAP_PW = "Eodndeodndeodnd1!"

today = datetime.today().strftime("%m.%d")
SAVE_PATH = f"C:/Users/USER/Desktop/SnOPWeb/input_data/품절예상조회/품절예상조회_{today}.xlsx"

def download_sap_data():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {
    "download.default_directory": r"C:\Users\USER\Desktop\SnOPWeb\input_data\품절예상조회",
    "download.prompt_for_download": False,
})

    driver = webdriver.Chrome(
        service=Service(r"C:\Users\USER\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"),
        options=options
    )
    wait = WebDriverWait(driver, 30)

    try:
         # ① 기존 파일 먼저 삭제 (다운로드 전에!)
        download_dir = r"C:\Users\USER\Desktop\SnOPWeb\input_data\품절예상조회"
        existing_files = glob.glob(os.path.join(download_dir, "*.xlsx"))
        for f in existing_files:
            os.remove(f)
            print(f"🗑️ 기존 파일 삭제: {f}")
        # ① 로그인
        driver.get(SAP_URL)
        wait.until(EC.presence_of_element_located((By.ID, "USERNAME_FIELD-inner")))
        driver.find_element(By.ID, "USERNAME_FIELD-inner").send_keys(SAP_ID)
        driver.find_element(By.ID, "PASSWORD_FIELD-inner").send_keys(SAP_PW)
        driver.find_element(By.ID, "LOGIN_LINK").click()
        #driver.save_screenshot("01_로그인완료.png")
        print("✅ 로그인 완료")

        # ② 메뉴 이동
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '품절 예상 조회')]")))
        driver.find_element(By.XPATH, "//*[contains(text(), '품절 예상 조회')]").click()
        #driver.save_screenshot("02_메뉴이동완료.png")
        print("✅ 메뉴 이동 완료")

        # 새 창 전환
        time.sleep(3)
        driver.switch_to.window(driver.window_handles[-1])
        print("✅ 새 창 전환 완료")

        # iframe 전환
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
            print("✅ iframe 전환 완료")
        except:
            print("ℹ️ iframe 없음, 계속 진행")

        # ③ 플랜트 입력 후 F8 실행
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[title='플랜트']")))
        plant_field = driver.find_element(By.CSS_SELECTOR, "input[title='플랜트']")
        plant_field.clear()
        plant_field.send_keys("1510")
        print("✅ 플랜트 입력 완료")
        time.sleep(1)
        plant_field.send_keys(Keys.F8)
        #driver.save_screenshot("03_조회완료.png")
        print("✅ 조회 완료")

        # ④ 엑스포트 버튼 클릭
        wait.until(EC.element_to_be_clickable((By.ID, "_MB_EXPORT102")))
        driver.find_element(By.ID, "_MB_EXPORT102").click()
        print("✅ 엑스포트 메뉴 열림")
        time.sleep(2)  # 메뉴 열릴 때까지 대기

        # # 스프레드시트 클릭
        # 방법 1 - aria-label로 찾기
        try:
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "tr[aria-label='스프레드시트']")))
            driver.find_element(By.CSS_SELECTOR, "tr[aria-label='스프레드시트']").click()
            print("✅ 스프레드시트 선택 완료 (방법1)")
        except:
            # 방법 2 - 텍스트로 찾기
            try:
                wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '스프레드시트')]")))
                driver.find_element(By.XPATH, "//*[contains(text(), '스프레드시트')]").click()
                print("✅ 스프레드시트 선택 완료 (방법2)")
            except:
                # 방법 3 - id로 찾기
                wait.until(EC.element_to_be_clickable((By.ID, "menu_MB_EXPORTI02_1_1")))
                driver.find_element(By.ID, "menu_MB_EXPORTI02_1_1").click()
                print("✅ 스프레드시트 선택 완료 (방법3)")

        # 엑스포트... 버튼 클릭
        # 엑스포트 형식 팝업 → "엑스포트..." 버튼 클릭
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[title='데이터 엑스포트 (Shift+F8)']")))
        driver.find_element(By.CSS_SELECTOR, "[title='데이터 엑스포트 (Shift+F8)']").click()
        print("✅ 엑스포트 클릭 완료")

        # 확인 버튼 클릭
        wait.until(EC.element_to_be_clickable((By.ID, "UpDownDialogChoose")))
        driver.find_element(By.ID, "UpDownDialogChoose").click()
        time.sleep(3)
        #driver.save_screenshot("05_다운로드완료.png")
        print(f"✅ 저장 완료: {SAVE_PATH}")

    except Exception as e:
        driver.save_screenshot("error_캡처.png")
        print(f"❌ 에러 발생: {e}")

    finally:
        # 다운로드 완료 대기 (최대 30초)
        for _ in range(30):
            files = glob.glob(os.path.join(download_dir, "*.xlsx"))
            crdownload = glob.glob(os.path.join(download_dir, "*.crdownload"))
            if files and not crdownload:
                break
            time.sleep(1)

        # 다운로드된 파일을 원하는 이름으로 변경
        files = glob.glob(os.path.join(download_dir, "*.xlsx"))
        latest_file = max(files, key=os.path.getctime)
        os.rename(latest_file, SAVE_PATH)
        print(f"✅ 파일 저장 완료: {SAVE_PATH}")

        driver.quit()

download_sap_data()

# def job():
#     print("🕘 자동 실행 시작!")
#     download_sap_data()

# # 매일 오전 9시 실행
# schedule.every().day.at("09:00").do(job)

# print("✅ 스케줄러 시작 - 매일 09:00 실행")
# while True:
#     schedule.run_pending()
#     time.sleep(60)