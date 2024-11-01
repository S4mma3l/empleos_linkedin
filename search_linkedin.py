import tkinter as tk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pickle
import os
import time
from cryptography.fernet import Fernet

# Generar una clave para encriptar y desencriptar
def generate_key():
    return Fernet.generate_key()

# Guardar la clave en un archivo
def save_key(key, filename="secret.key"):
    with open(filename, "wb") as key_file:
        key_file.write(key)

# Cargar la clave desde el archivo
def load_key(filename="secret.key"):
    return open(filename, "rb").read()

# Encriptar cookies
def encrypt_cookies(cookies, key):
    fernet = Fernet(key)
    return fernet.encrypt(pickle.dumps(cookies))

# Desencriptar cookies
def decrypt_cookies(encrypted_cookies, key):
    fernet = Fernet(key)
    return pickle.loads(fernet.decrypt(encrypted_cookies))

# Archivo de cookies
cookies_file = "linkedin_cookies.pkl"
key_file = "secret.key"

# Verificar si la clave ya existe, si no, generar y guardar una
if not os.path.exists(key_file):
    key = generate_key()
    save_key(key)
else:
    key = load_key()

def save_cookies(driver):
    encrypted_cookies = encrypt_cookies(driver.get_cookies(), key)
    with open(cookies_file, "wb") as f:
        f.write(encrypted_cookies)

def load_cookies(driver):
    if os.path.exists(cookies_file):
        with open(cookies_file, "rb") as f:
            encrypted_cookies = f.read()
            cookies = decrypt_cookies(encrypted_cookies, key)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return True
    return False

def login_and_save_cookies(driver, username, password):
    driver.get("https://www.linkedin.com/login")
    username_field = driver.find_element(By.ID, "username")
    password_field = driver.find_element(By.ID, "password")
    username_field.send_keys(username)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)

    # Esperar el ingreso del código de 2FA
    input("Ingresa el código de 2FA y presiona Enter para continuar...")
    save_cookies(driver)

def search_jobs():
    # Obtener valores de entrada
    keywords = entry_keywords.get()
    locations = entry_locations.get()

    # Configurar el controlador para Firefox
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service)

    try:
        # Cargar cookies si existen para evitar autenticación
        driver.get("https://www.linkedin.com")
        if not load_cookies(driver):
            username = entry_username.get()
            password = entry_password.get()
            login_and_save_cookies(driver, username, password)

        # Acceder a la sección de empleos
        driver.get("https://www.linkedin.com/jobs/")
        
        # Buscar empleos
        search_jobs_on_linkedin(driver, keywords, locations)
        
    except Exception as e:
        job_list.insert(tk.END, f"Error: {str(e)}")
    finally:
        driver.quit()

def search_jobs_on_linkedin(driver, keywords, locations):
    try:
        # Esperar a que el campo de búsqueda de empleos esté presente
        search_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@role='combobox']"))
        )
        search_box.send_keys(keywords)
        search_box.send_keys(Keys.RETURN)
        job_list.insert(tk.END, "Buscando empleos...")
        
        # Esperar resultados
        time.sleep(5)

        # Filtrar por ubicaciones y remoto
        job_list.insert(tk.END, "Filtrando por ubicación y remoto...")
        filter_location(driver, locations)
        filter_remote(driver)

        # Extraer enlaces de empleos
        job_list.insert(tk.END, "Extrayendo enlaces de empleos...")
        job_links = extract_job_links(driver)

        # Mostrar enlaces en la interfaz
        display_links(job_links)

        # Opcional: Enviar solicitudes de conexión
        job_list.insert(tk.END, "Conectando con reclutadores...")
        connect_with_recruiters(driver, job_links)

    except TimeoutException:
        job_list.insert(tk.END, "Error: El campo de búsqueda de empleos no se encontró.")

def filter_location(driver, locations):
    try:
        location_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Ubicación']"))
        )
        for location in locations.split(","):
            location_box.clear()  # Limpiar el campo antes de ingresar nueva ubicación
            location_box.send_keys(location.strip())
            location_box.send_keys(Keys.RETURN)
            time.sleep(2)
    except Exception as e:
        job_list.insert(tk.END, f"Error al encontrar el campo de ubicación: {str(e)}")


def filter_remote(driver):
    try:
        remote_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Remoto']"))
        )
        remote_button.click()
        time.sleep(2)
    except TimeoutException:
        job_list.insert(tk.END, "Error: No se pudo encontrar el botón 'Remoto'.")

def extract_job_links(driver):
    job_links = []
    jobs = driver.find_elements(By.CLASS_NAME, 'base-card__full-link')
    for job in jobs[:10]:  # Limitar resultados para simplicidad
        job_links.append(job.get_attribute('href'))
    return job_links

def display_links(links):
    job_list.delete(0, tk.END)  # Limpiar lista antes de mostrar nuevos resultados
    for link in links:
        job_list.insert(tk.END, link)

def connect_with_recruiters(driver, job_links):
    for link in job_links:
        driver.get(link)
        time.sleep(2)
        try:
            # Busca el perfil de recursos humanos en la página de trabajo y envía solicitud
            hr_profiles = driver.find_elements(By.XPATH, "//a[contains(@href, 'recruiter')]")
            for profile in hr_profiles:
                driver.get(profile.get_attribute('href'))
                time.sleep(1)
                connect_button = driver.find_element(By.XPATH, "//button[text()='Conectar']")
                connect_button.click()
                time.sleep(1)
                send_invite_button = driver.find_element(By.XPATH, "//button[text()='Enviar']")
                send_invite_button.click()
                time.sleep(2)
                job_list.insert(tk.END, f"Solicitud enviada a {profile.get_attribute('href')}")
        except Exception as e:
            job_list.insert(tk.END, f"Error al conectar con reclutadores: {str(e)}")

# Configuración de la interfaz de usuario (GUI) con Tkinter
root = tk.Tk()
root.title("LinkedIn Job Finder")

# Entradas de usuario
tk.Label(root, text="Usuario:").grid(row=0, column=0)
entry_username = tk.Entry(root, width=50)
entry_username.grid(row=0, column=1)

tk.Label(root, text="Contraseña:").grid(row=1, column=0)
entry_password = tk.Entry(root, show="*", width=50)
entry_password.grid(row=1, column=1)

tk.Label(root, text="Palabras clave:").grid(row=2, column=0)
entry_keywords = tk.Entry(root, width=50)
entry_keywords.grid(row=2, column=1)
entry_keywords.insert(0, "Jr pentester, pentester, Jr developer, python")

tk.Label(root, text="Ubicaciones:").grid(row=3, column=0)
entry_locations = tk.Entry(root, width=50)
entry_locations.grid(row=3, column=1)
entry_locations.insert(0, "Costa Rica, España, Estados Unidos")

# Botón de búsqueda
search_button = tk.Button(root, text="Buscar Empleos", command=search_jobs)
search_button.grid(row=4, column=0, columnspan=2, pady=10)

# Listado de enlaces de empleos
job_list = tk.Listbox(root, width=80, height=20)
job_list.grid(row=5, column=0, columnspan=2)

# Ejecutar aplicación
root.mainloop()