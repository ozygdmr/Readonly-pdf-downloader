import os
import time
import io
import pymupdf  # fitz yerine doğrudan pymupdf
import pytesseract
from PIL import Image
from playwright.sync_api import sync_playwright

# Windows'ta Tesseract PATH'e ekli değilse başındaki # işaretini kaldır:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def drive_pdf_otomatik_indir(drive_url, cikti_dosyasi="cikti.pdf", dil="tur+eng"):
    sayfa_gorselleri = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1080}, device_scale_factor=2)
        page = context.new_page()

        print("Bağlantı açılıyor ve sayfa yükleniyor...")
        page.goto(drive_url, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        if "accounts.google.com" in page.url:
            print("Hata: Bu dosya herkese açık değil, erişim yetkisi (hesap girişi) gerektiriyor.")
            browser.close()
            return

        print("Sayfalar taranıyor...")
        onceki_yukseklik = 0
        
        for _ in range(100):
            page.mouse.wheel(0, 800)
            time.sleep(0.6)
            yeni_yukseklik = page.evaluate("document.documentElement.scrollHeight")
            
            page.evaluate("""
                document.querySelectorAll('div').forEach(div => {
                    if (div.scrollHeight > div.clientHeight + 100) {
                        div.scrollTop += 800;
                    }
                });
            """)
            
            if _ > 5 and yeni_yukseklik == onceki_yukseklik:
                time.sleep(1)
            onceki_yukseklik = yeni_yukseklik

        img_elements = page.locator("img[src^='blob:'], img[src*='drive.google.com']").all()
        
        if not img_elements:
            page.keyboard.press("Home")
            time.sleep(1)
            for i in range(50):
                screenshot_bytes = page.screenshot()
                sayfa_gorselleri.append(screenshot_bytes)
                page.keyboard.press("PageDown")
                time.sleep(0.8)
                if i > 0 and sayfa_gorselleri[-1] == sayfa_gorselleri[-2]:
                    sayfa_gorselleri.pop()
                    break
        else:
            print(f"Toplam {len(img_elements)} sayfa bulundu. Yakalanıyor...")
            for img in img_elements:
                try:
                    box = img.bounding_box()
                    if box and box["width"] > 300 and box["height"] > 400:
                        img.scroll_into_view_if_needed()
                        time.sleep(0.4)
                        sayfa_gorselleri.append(img.screenshot())
                        print(f"Sayfa {len(sayfa_gorselleri)} alındı.")
                except Exception:
                    continue

        browser.close()

    if not sayfa_gorselleri:
        print("Hata: Sayfalar yakalanamadı.")
        return

    print("\nMetinler kopyalanabilir hale getiriliyor (OCR)...")
    birlesik_pdf = pymupdf.open()

    for i, img_bytes in enumerate(sayfa_gorselleri, start=1):
        print(f"İşleniyor: Sayfa {i}/{len(sayfa_gorselleri)}")
        pil_img = Image.open(io.BytesIO(img_bytes))
        ocr_pdf_bytes = pytesseract.image_to_pdf_or_hocr(pil_img, extension='pdf', lang=dil)
        tek_sayfa_pdf = pymupdf.open("pdf", ocr_pdf_bytes)
        birlesik_pdf.insert_pdf(tek_sayfa_pdf)

    birlesik_pdf.save(cikti_dosyasi)
    birlesik_pdf.close()
    print(f"\nTamamlandı! Dosya kaydedildi: {os.path.abspath(cikti_dosyasi)}")

if __name__ == "__main__":
    link = input("Google Drive PDF linkini yapıştırın: ").strip()
    dosya_adi = input("Kaydedilecek PDF adı (varsayılan: cikti.pdf): ").strip() or "cikti.pdf"
    if not dosya_adi.endswith(".pdf"):
        dosya_adi += ".pdf"
        
    drive_pdf_otomatik_indir(link, dosya_adi)