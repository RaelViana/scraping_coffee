import schedule
import time
import carrefour_scraping  # Importando como módulo
import extra_scraping


def run_carrefour():
    carrefour_scraping.main()  # Chamada do script_ executando metodo`main()`
    print("Tarefa executada com sucesso !!!")
    
def run_extra():
    extra_scraping.main()
    print("Tarefa executada com sucesso !!!")


schedule.every().day.at("08:00").do(run_carrefour) ## Escredulador programado para rodar diariamente no horario especificado
schedule.every().day.at("08:10").do(run_extra)



while True:
    schedule.run_pending()
    time.sleep(3)
