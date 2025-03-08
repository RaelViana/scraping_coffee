import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def get_page_content(url, headers, parameters):
    response = requests.get(url, headers=headers, params=parameters).text
    soup = BeautifulSoup(response, 'html.parser')
    return soup

def parse_produtos(soup):    
    table_geral = soup.find('div', class_='flex-1')
    produtos = []
    rows = table_geral.find_all('a', class_="border rounded-lg border-[#f2f2f2] p-2 cursor-pointer overflow-hidden hover:shadow-md undefined flex flex-col gap-4")
    
    for row in rows:
        nome_produto = row.find('h2', class_='text-xs leading-4 text-[#333] text-left my-1 truncate-text h-12')
        valor_produto = row.find('span', class_='text-base font-bold text-default-dark')
        url_product = DOMAIN + row['href']
        
        if nome_produto and valor_produto:
            nome = nome_produto.get_text().strip()
            valor_text = valor_produto.get_text().strip()
            valor = float(valor_text[3:8].replace(',', ''))
            link = url_product
            nome = nome.encode('latin1').decode('utf-8')
            
            if nome.startswith("Café"):  ## Lista apenas produtos que começam com a palavra
                produto = {'produto': nome, 'valor': valor, 'link': link}    
                produtos.append(produto)
                
    return produtos

def send_email(produto, valor, link, loja):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    email_user = 'seu_email@gmail.com'
    email_password = 'pass' # Senha gerada para aplicativos, caso tenha 2FA no Gmail
    to_email = 'email_destinatario@gmail.com'

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = to_email
    msg['Subject'] = f'Atenção {produto} em promoção !!!'

    html_body = f'''
    <p><strong><span style="font-size: 16px;">Detalhes da promoção, confira !!!</span></strong></p>

        <p><strong>Esta disponivel no {loja} HIPERMERCADO</strong></p>
        <p><strong>Item/Produto:</strong> {produto}</p>
        <p><strong>Valor:</strong> R$ {valor / 100:.2f}</p>
        <p><strong>Link para compra:</strong> <a href="{link}">Clique aqui</a></p>

        <p>Aproveite oferta por tempo limitado.</p>
        
        <p>Att.,</p>
        <p>Rael Viana</p>
        
        '''
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_user, email_password)
            server.sendmail(email_user, to_email, msg.as_string())
            print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

def main():
    global DOMAIN
    DOMAIN = 'https://mercado.carrefour.com.br'
    URL = f'{DOMAIN}/busca/cafe%20500g'
    HEADERS = {'User-agent': 'Google Mozilla/5.0'}
    PARAMETERS = {'utf8': '✔', 'page': 1}
    
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
    df_products['loja'] = 'CARREFOUR'
    filtro = df_products["produto"].str.contains("500 g|500g", case=False, na=False) & (df_products["valor"] <= 2550)

    for _, row in df_products[filtro].iterrows():
        send_email(row["produto"], row["valor"], row["link"], row['loja'])
    
    df_products['preco'] = (df_products['valor'] / 100).apply(lambda x: f" {x:,.2f}".replace('.', ','))
    df_prod_final = df_products[['data', 'produto', 'preco', 'loja', 'link']].copy()
    
    path = "/home/seu/path/carrefour"
    # path = "/home/rael/Dev/Web_Scraping/teste"
    os.makedirs(path, exist_ok=True)
    save_date = datetime.today().strftime('%d-%m-%Y')
    file_path_excel = os.path.join(path, f'lista_carrefour_{save_date}.xlsx')
    df_prod_final.to_excel(file_path_excel, index=False)
    file_path_csv = os.path.join(path, f'lista_carrefour_{save_date}.csv')
    df_prod_final.to_csv(file_path_csv, index=False)
    
    print(df_products)
    print(f'Arquivo Excel salvo em: {file_path_excel}')
    print(f'Arquivo CSV salvo em: {file_path_csv}')

if __name__ == "__main__":
    main()