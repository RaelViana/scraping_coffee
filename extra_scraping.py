import os
import time
import smtplib
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def get_page_content(url, headers, parameters):
    # Configurar o Selenium
    options = Options()
    options.add_argument("--headless")  # Roda sem abrir o navegador
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    
    driver.get(url)

    # Aguarda um tempo inicial para carregar os primeiros produtos
    time.sleep(3)

    # Rola a página várias vezes para forçar o carregamento de novos produtos
    previous_height = driver.execute_script("return document.body.scrollHeight")

    for _ in range(10):  # Tenta rolar até 10 vezes
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Tempo para novos produtos carregarem

        # Verifica se a página carregou mais produtos
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == previous_height:
            break  # Para de rolar se não carregar mais nada
        previous_height = new_height

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    return soup


def parse_produtos(soup):

    table_geral = soup.find(
        "div",
        class_="MuiGrid-root sc-6scn59-0 grqZtK MuiGrid-container MuiGrid-spacing-xs-1",
    )
    produtos = []
    rows = table_geral.find_all(
        "div",
        class_="MuiGrid-root sc-6scn59-0 jwYpAF MuiGrid-item MuiGrid-grid-xs-6 MuiGrid-grid-sm-4 MuiGrid-grid-md-3 MuiGrid-grid-lg-2 MuiGrid-grid-xl-2",
    )

    for row in rows:
        nome_produto = row.find("img")["alt"]
        valor_produto = row.find("p", class_="PriceValue-sc-20azeh-4 hHjSYF")
        url_product = row.find("a")["href"]

        if nome_produto and valor_produto:
            nome = nome_produto.strip()
            valor_text = valor_produto.get_text().strip()
            valor = valor_text[3:8]
            valor = valor.replace(",", "")
            valor = float(valor)
            link = url_product


            if nome.startswith("Café Torrado"):  # Verifica se o nome começa com "Café"
                produto = {"produto": nome, "valor": valor, "link": link}
                produtos.append(produto)

    return produtos


def send_email(produto, valor, link, loja):
    # Configurações do servidor SMTP (usando Gmail como exemplo)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    email_user = "seu_email@gmail.com"  # Seu e-mail
    email_password = (
        "Password"  # Senha gerada para aplicativos, caso tenha 2FA no Gmail
    )

    # Destinatário
    to_email = "destinatario@gmail.com"

    # Criando a mensagem
    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = to_email
    msg["Subject"] = f"Atenção {produto} em promoção !!!"

    # Corpo do e-mail em HTML
    html_body = f"""
   <p><strong><span style="font-size: 16px;">Detalhes da promoção, confira !!!</span></strong></p>

    <p><strong>Esta disponivel no {loja} HIPERMERCADO</strong></p>
    <p><strong>Item/Produto:</strong> {produto}</p>
    <p><strong>Valor:</strong> R$ {valor / 100:.2f}</p>
    <p><strong>Link para compra:</strong> <a href="{link}">Clique aqui</a></p>

    <p>Aproveite oferta por tempo limitado.</p>
    
    <p>Att.,</p>
    <p>Rael Viana</p>
    
    """

    msg.attach(MIMEText(html_body, "html"))

    # Enviando o e-mail via SMTP
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Criptografando a conexão
            server.login(email_user, email_password)  # Fazendo login
            server.sendmail(email_user, to_email, msg.as_string())  # Enviando o e-mail
            print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")


def main():
    global DOMAIN
    DOMAIN = "https://www.clubeextra.com.br"  #### site a ser extraido
    URL = f"{DOMAIN}/busca?terms=cafe%20500g"  ### URL completa para raspagem 'ENDPOINT'
    HEADERS = {"User-agent": "Google Mozilla/5.0"}  ### servidor de origem extração
    PARAMETERS = {"utf8": "✔", "page": 1}
    
    page = 1
    produtos_unicos = set()
    todos_produtos = []
    data_atual = datetime.today().strftime('%d-%m-%Y %H:%M:%S')
    MAX_PAGES = 10
    
    while page <= MAX_PAGES:
        PARAMETERS['page'] = page
        soup_produtos = get_page_content(URL, HEADERS, PARAMETERS)
        itens = parse_produtos(soup_produtos)
        
        if not itens:
            break

        novos_itens = []
        for item in itens:
            nome, valor = item.get("produto"), item.get("valor")
            chave_unica = (nome, valor)
            
            if chave_unica not in produtos_unicos:
                produtos_unicos.add(chave_unica)
                item = {"data": data_atual, **item}
                novos_itens.append(item)
        
        todos_produtos.extend(novos_itens)
        page += 1
    
    df_products = pd.json_normalize(todos_produtos)
    df_products['loja'] = 'EXTRA'
    filtro = df_products["produto"].str.contains("500 g|500g", case=False, na=False) & (df_products["valor"] <= 2550) # Filtro promoção

    for _, row in df_products[filtro].iterrows():
        send_email(row["produto"], row["valor"], row["link"], row['loja'])
    
    df_products['preco'] = (df_products['valor'] / 100).apply(lambda x: f" {x:,.2f}".replace('.', ','))
    df_prod_final = df_products[['data', 'produto', 'preco', 'loja', 'link']].copy()
    
    path = "/home/seu/path/extra"
    os.makedirs(path, exist_ok=True)
    save_date = datetime.today().strftime('%d-%m-%Y')
    file_path_excel = os.path.join(path, f'lista_extra_{save_date}.xlsx')
    df_prod_final.to_excel(file_path_excel, index=False)
    file_path_csv = os.path.join(path, f'lista_extra_{save_date}.csv')
    df_prod_final.to_csv(file_path_csv, index=False)
    
    print(df_products)
    print(f'Arquivo Excel salvo em: {file_path_excel}')
    print(f'Arquivo CSV salvo em: {file_path_csv}')

if __name__ == "__main__":
    main()