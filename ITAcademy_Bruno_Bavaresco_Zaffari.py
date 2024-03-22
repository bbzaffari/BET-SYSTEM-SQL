import sys # Para sair do programa e funcionalidades do sistema
import time
import random # Para gerar os numeros aleatorios do sorteio
#import numpy as np # Era para usar o random.rand n foi necessario e talvez use
import threading # Para atualizar o tempo
import psycopg2 as pg2 # Para conectar ao banco de dados PostqreSQL
#import itertools as it # Caso necessario, Estava tentando pensar em usar permutacao de alguma forma mas n sei se vou implementar até o final do programa
import collections as cl # Para contar a frequencia dos numeros
from datetime import datetime # Para pegar a data e hora atual
from collections import Counter # Para contar a frequencia dos numeros
from collections import defaultdict # Para criar dicionarios com valores padrao, para nao dar erro caso inserirmos diretamente um valor

# O sistema funciona com o server do PostgreSQL e precisa instalar-lo em sua maquina no site( o programa ja instala o pgadmin):
# https://www.postgresql.org/download/
# O SGBD foi escolido pois o aluno tem mais conhecimento a respeito mas é um sistema bem bom para implementar funcionalidades junto com o Python visto que possui a biblioteca psycopg2
# Caso n tenha a biblioteca psycopg2, instale com o comando: pip install psycopg2
# Em abrir_conexao_e_cursor() MUDE o database, user e password para o nome do seu banco de dados, seu user e sua senha
# '-' Foi posto como forma de facilitar a leitura da saida do programa e pra ficar bonito por isso tem muitos '-' e '-\n', pois n sei fazer interface grafica mas tentei o melhor
# O sistema conta com varios controles para evitar erros e para garantir que o usuario insira os dados corretamente
# O sistema funciona com uma maquina de estados verificando o horario sendo que entre 8 e 20 horas é possivel fazer apostas e entre 20 e 8 horas é possivel ver o resultado do sorteio
# '-> Caso esteja testando o progrma e queira ver o resultado do sorteio e nao esperar até as 20 horas, pode alterar as variaveis INICIO_APOSTAS e FIM_APOSTAS 
# O sistema conta com uma senha de administrador para sair do procrama, pois se presume que na primeira vez que o programa rodará sera numa maquina fisica que nao permita sair abruptamente do sistema.
# Pode ser usado ctrl+c para sair do programa sem problemas pois o sistema fecha a conexao com o banco de dados e realiza a limpeza necessaria
# O sistema de apostas IT ACADEMY é um sistema de apostas sem fim lucrativos e sem necessidade de verab para manutensao, sendo assim quando n tiver ganhador
# o premio acumula em totalidade para o proximo sorteio

# Lista compartilhada para armazenar inputs do usuário
input_list = []

# Lock para sincronizar o acesso à lista
list_lock = threading.Lock()

FIM = 20# Variavel do fim das apostas -------------------------------------> (MUDAR SE NECESSARIO)
INICIO = 8# Variavel do inicio das apostas --------------------------------> (MUDAR SE NECESSARIO)
dia_anterior = -1# Dia anterior é util para saber se o diapassou e criar uma nova tabela/mas na verdade n se trata do dia anterior
cur_global = None# Variavel global do cursor
conn_global = None# Variavel global de conexao
controle_sorteio = 0# Controle para evitar que o sorteio seja feito mais de uma vez
#controle_primeira_vez = 0# Caso excluiu o a tabela sorteio e ta testando isso entre as 00 e 8h(Raro)
controle_criacao_tabela = 0#Controle para criar tabela
#where_it_is = 0# Variavel para saber onde esta o programa(0 = nada, 1 = apostas, 2 = resultado do sorteio)
status = 0# Variavel para saber onde esta o programa(0 = nada, 1 = apostas, 2 = resultado do sorteio)

senha_adm = "00"
# Só pra inicializar as variaveis, pq tava testando antes
hora = datetime.now().hour# Pega a hora atual
segundo = datetime.now().second# Pega o segundo atual
minuto = datetime.now().minute# Pega o minuto atual
dia = datetime.now().day# Pega o dia atual
mes = datetime.now().month# Pega o mes atual
ano = datetime.now().year# Pega o ano atual

def thread_atualiza_tempo():# Funcao para atualizar a hora e o minuto
    # Alem disso, a funcao verifica se o horario de apostas ja passou ou se ja comecou
    global hora, minuto, segundo, dia, mes, ano, INICIO, FIM
    while True:
        agora = datetime.now()
        dia, mes, ano = agora.day, agora.month, agora.year
        hora, minuto, segundo = agora.hour, agora.minute, agora.second
        # if hora>= FIM or hora < INICIO:# Verifica se o horario de apostas ja passou ou se esta antes da proxima rodada
        #     # print("-")
        #     # print("Sentimos, mas as apostas estão fechadas no momento.")
        #     where_it_is = 2
        # if INICIO <= hora < FIM:# Verifica se esta dentro do horario de apostas
        #     # print("-")
        #     # print("Sentimos, mas as apostas começaram agora!")
        #     where_it_is = 1
        time.sleep(1)
#Essa função é para pegar o input do usuário e adicionar à lista de forma thread-safe
#é a responsavel pelo input n bloquear e conseguir mudar de estados
def input_t():# Monopolisa o stdin
    while True:
        try:
            user_input = input()# Recebe input do usuário
            with list_lock:# Adiciona o input à lista de forma thread-safe
                input_list.append(user_input)
        except ValueError:
            print("Valor invalido!")
        
def ininput():
    user_input = 0
    if input_list:# Remove e retorna o primeiro item da lista
        with list_lock:# Processa inputs da lista de forma thread-safe
            user_input = input_list.pop(0)
    elif INICIO <= hora < FIM and status == 2:# Ta em sorteio e é periodo de apostas
        user_input = True
    elif (hora>= FIM or hora < INICIO) and status == 1:# Ta em apostas e é periodo de sorteio
        user_input = True
    time.sleep(0.1)    
    return user_input

def abrir_conexao_e_cursor(): # Função para abrir a conexão com o banco de dados e retornar o cursor e a conexão para garantir que o fechar_...  feche e n fique aberta mesmo q o programa acabe(ou por conta do user ou ctrl+c)
    global conn_global
    global cur_global
    conn_global = pg2.connect(database='postgres', user='postgres', password='04111999')
    cur_global = conn_global.cursor()
    #print("Conexao aberta com sucesso!")# Debug
    return  cur_global, conn_global

def fechar_conexao_e_cursor():
    global conn_global
    global cur_global
    if cur_global is not None:
        cur_global.close()
    if conn_global is not None:
        conn_global.close()
        conn_global = None
    #print("Conexao fechada com sucesso!")# Debug
        
def menu():# Menu e funcionalidades
    #global FIM, INICIO
    global dia_anterior# Dia anterior é util para saber se o diapassou e criar uma nova tabela
    global controle_sorteio# Controle para evitar que o sorteio seja feito mais de uma vez
    global controle_criacao_tabela#Controle para criar tabela 
    global status# Variavel para saber onde esta o programa(0 = nada, 1 = apostas, 2 = resultado do sorteio)
    #global controle_primeira_vez
    
    data_formatada = f"{ano}{mes:02d}{dia:02d}"# Corrige a formatação da data para pormos como nome da tabela
    tabela_nome = f"apostas_{data_formatada}" # Define um nome único para a tabela com base na data
    #print(f"Data: {dia}/{mes}/{ano} Hora: {hora}:{minuto}:{segundo}\n-")# Debug
        
    if dia != dia_anterior:  # Verifica se o dia mudou para criar uma nova tabela
        controle_sorteio = 0
        dia_anterior = dia
        #print(dia_anterior)# Debug
        #print("Dia mudou")# Debug
        cur, conn = abrir_conexao_e_cursor() # Conecta ao banco de dados e retorna cursor e conexao
        # ---------------------------------------------------------- Escolha dos tipos de variavel:------------------------------------------------------------------------------------------------|
        # ID SERIAL PRIMARY KEY,        -> SERIAL pois nao precisa de incercao é tipico para Primari Key                                                                                           |
        # NOME VARCHAR(72),             -> Presumi um espaco de no maximo 72 caracteres no nome se nao ficaria ruim de imprimir                                                                    |
        # CPF BIGINT CHECK (LENGTH(CAST(CPF AS VARCHAR)) < 11),-> BIGINT pois se fossem 11 digitos ocuparia mais memoria                                                                           |
        # APOSTA VARCHAR(18),           -> Aposta sera varchar pois depois com Counter de collections sera mais facil de ver a frequencia dos numeros                                              |
        # HORA_DA_APOSTA TIMESTAMP      -> Não sera usado mas é sempre melhor termos mais informacoes do que menos quando estamos criando uma tabela pois nao podemos adicionar informacao depois  |
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        # Tabela tabela_data conterá todas as apostas feitas no dia
        query = f'''
            CREATE TABLE IF NOT EXISTS {tabela_nome}(
                ID SERIAL PRIMARY KEY,
                NOME VARCHAR(81),
                CPF VARCHAR(11) CHECK (LENGTH(CPF) = 11),
                APOSTA VARCHAR(18),
                HORA_DA_APOSTA TIMESTAMP
            )
        '''
        # opcao pois ocupa menos espaco, mas tira o '0' a esquerda e nao serafeito operacao aritimetica
        #CPF BIGINT CHECK ((LENGTH(CAST(CPF AS VARCHAR)) = 11) OR (LENGTH(CAST(CPF AS VARCHAR)) = 10)) 
        # opcao pois n desformatara o CPF, mas um pouco mais especo
        #CPF VARCHAR(11) CHECK (LENGTH(CPF) = 11) 
        cur.execute(query)
        conn.commit()# Salva as alterações no banco de dados
        fechar_conexao_e_cursor()
        controle_criacao_tabela = 1# Cria tabela somente uma vez na inicializacao do programa ou na mudanca do dia
        #print(f"Tabela {tabela_nome} criada com sucesso!\n-") # Debug
        
        # Altera a sequencia para comecar do 1000-----------------------------------
        cur, conn = abrir_conexao_e_cursor() # Conecta ao banco de dados e retorna cursor e conexao
        query = f"SELECT COUNT(*) FROM {tabela_nome}"# Query para pegar a quantidade de apostas ja na tabela
        #útil pois se o programa cair ou fechar e tentar adicionar um outro indice n comecar do 1000 e dar erro
        #por isso temos q ver quantas apostas ja tem na tabela e comecar a partir do proximo numero
        cur.execute(query)
        indice = cur.fetchall()[0][0]# Pega a quantidade de apostas
        indice +=1000
        #print(quantidade_apostas)# Debug
        query = f"SELECT pg_get_serial_sequence('{tabela_nome}', 'id');"
        cur.execute(query)
        sequence = cur.fetchall()[0][0]
        query = f"ALTER SEQUENCE {sequence} RESTART WITH {indice};"
        cur.execute(query)
        conn.commit()
        fechar_conexao_e_cursor()
            
    if (hora>= FIM  and controle_sorteio == 0):# Inicia o sorteio, fora do horario das apostas tirei o (or hora < INICIO)
        status = 0
        # Mensagem --------------------------------------------------------------
        print("-" * 72)
        print("-" * 72)
        print("As apostas estão fechadas no momento.".center(72, "-"))
        print("Resultado do último sorteio: ".center(72, "-"))
        print("-" * 72)
        print("-" * 72)
        data_formatada = f"{ano}{mes:02d}{dia:02d}"
        #-------------------------------------------------------------------------
        Ganhadores(tabela_nome, data_formatada)# Verifica os ganhadores
        controle_sorteio = 1# Garante que seja escolido somente uma vez     
            
    if ((hora>= FIM) and controle_sorteio == 1) or (hora < INICIO): # Menu para ver o resultado do sorteio ou sorteios anteriores
        status = 2
        print("-\n"*9)
        print("-"*72)
        print("Aguardando novo sorteio".center(72, "-"))
        if hora < INICIO:
            print("O novo periodo de apostas começará amanhã às  8:00h".center(72, "-"))
        elif hora >= FIM:   
            print("O novo periodo de apostas começará às 8:00h".center(72, "-"))
        print("-"*72)
        while True:
            try:
                print("Escolha uma das opções abaixo:")
                print("1 - Ver relatório do sorteio passado")
                print("2 - Ver resultado de todos os sorteios anteriores")
                print("3 - Terminar o programa")
                print("-> ")
                while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                    x = ininput()
                    if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                        print("Sentimos, mas as apostas começaram agora!")
                        return 0
                    if isinstance(x, str):
                        break
                op = int(x)
                if op == 1:
                    Ganhadores(tabela_nome, data_formatada)
                elif op == 2:
                    imprime_sorteios()
                elif op == 3:
                    try:
                        print("Para sair do programa, informe a senha root: ")
                        while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                            x = ininput() 
                            if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                                print("Sentimos, mas as apostas começaram agora!")
                                return 0
                            if isinstance(x, str):
                                break
                        senha = x
                        if senha_adm == senha:
                            print(("-\n" * 6)[:-1])
                            print("Muito obrigado por usar nosso programa! Realizando limpeza e saindo\n-\n-\n-")
                            fechar_conexao_e_cursor()
                            sys.exit()
                    except ValueError:
                        print("Senha invalida!")
                else:
                    print("Opção invalida!")
            except ValueError:
                print("Opção invalida!") 

    if (INICIO <= hora < FIM):  # Verifica se está dentro do horário de apostas
        status = 1
        while True:
            try:
                # Mensagem inicial formatada -------------------------------------------------
                print("-" * 72)
                print("-" * 72)
                print("Bem-vindo ao sistema de apostas da Dell IT ACADEMY!".center(72, "-"))
                print("As apostas começam às 8:00 e terminam às 20:00".center(72, "-"))
                print("-" * 72)
                print("-" * 72)
                print("Escolha uma das opções abaixo:")
                print("1 - Aposta")
                print("2 - Verificar apostas feitas")
                print("3 - Funções especiais (Acesso restrito)")
                #-----------------------------------------------------------------------------
                print("-> ")
                while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                    x = ininput() 
                    if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                        print("Sentimos, mas o sorteio começará agora!")
                        return 0
                    if isinstance(x, str):
                        break
                op = int(x) #Não foi posto op 1,2,3 para se o ususario tiver em cima do horario(FIM) o programa na pula pro sorteio
                print("-")
                if op == 1:# Para realizar a aposta
                    aposta(tabela_nome) 
                elif op == 2:
                    verificar_aposta(tabela_nome)# Printa as informacoes da tabela no banco de dados de todas as apostas feitas no dia(Nome, aposta)
                elif op == 3:# Area reservada do administrador, com funcoes especificas 
                    # Nesse caso será para terminar o progr. caso tiver a senha correta
                    # Para gerar N apostas aleatorias e facilitar o teste do programa
                    # Ou para retornar ao menu
                    while True:
                        try:
                            print("Informe a senha root: ")
                            while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                                x = ininput() 
                                if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                                    print("Sentimos, mas o sorteio começará agora!")
                                    return 0
                                if isinstance(x, str):
                                    break
                            senha = x
                            print("-")
                            if senha_adm == senha:
                                print("-" * 54)
                                print("Senha Válida!")
                                
                                while True:
                                    try:
                                        print("-" * 54)
                                        print("Informe a opção desejada:")
                                        print("3->(1) Terminar o programa")
                                        print("3->(2) Inserir N apostas de números aleatórios na tabela") 
                                        print("3->(3) Voltar ao menu")
                                        print("-> ")
                                        while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                                            x = ininput() 
                                            if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                                                print("Sentimos, mas o sorteio começará agora!")
                                                return 0
                                            if isinstance(x, str):
                                                break
                                        op = int(x)
                                        print("-" * 54)
                                        if op == 1:
                                            print(("-\n" * 6)[:-1])
                                            print("Muito obrigado por usar nosso programa! Realizando limpeza e saindo\n-\n-\n-")
                                            fechar_conexao_e_cursor() # Fecha a conexão atual se estiver aberta
                                            sys.exit()
                                        elif op == 2:
                                            print("Digite a quantidade de inserções de números aleatórios(N)\nque deseja gerar(N, max e min, respectivamente: 1000 e 1):")
                                            while True:
                                                try:
                                                    print("-> ")
                                                    while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                                                        x = ininput() 
                                                        if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                                                            print("Sentimos, mas o sorteio começará agora!")
                                                            return 0
                                                        if isinstance(x, str):
                                                            break
                                                    N = int(x)
                                                    if N <= 0:
                                                        N = 1
                                                    elif N >= 1000:
                                                        N = 1000
                                                    SQL_INSERTION(tabela_nome, N)
                                                    break
                                                except ValueError:
                                                    print("Opção invalida!")
                                        elif op == 3:
                                            print("Voltando ao Menu")
                                            break
                                        else:
                                            print("Opção invalida!")
                                    except ValueError:
                                        print("Opção invalida!")
                            else:
                                print("Senha invalida!\n-")
                            break
                        except ValueError:
                            print("Senha invalida!\n-")
                else:
                    print("Opção inválida")
                    menu()# volta para o menu caso a opcao seja invalida  
            except ValueError:
                print("Opção invalida!")        
        return 0  
    
def Acumulo(): # Pega o acumulo se tiver pelo menos uma linha
    query ="SELECT COUNT(*) FROM SORTEIO" # Ve se ja tem uma linha pelo menos
    cur, conn = abrir_conexao_e_cursor() 
    cur.execute(query)
    tam = cur.fetchall()[0]
    if tam[0] == 0:
        acum = 0
    else:
        query = """SELECT ACUMULO FROM SORTEIO
        ORDER BY ID DESC
        LIMIT 1;
        """
        cur.execute(query)
        acumulo = cur.fetchall()[0][0]# primeiro elemento da primeira tupla(unica tulpa)
        acum = int(acumulo)
    #print(f"Acumulo: R$ {acum}")
    fechar_conexao_e_cursor()
    return acum
def imprime_sorteios():# Imprime todos os sorteios
    query = "SELECT COUNT(*) FROM SORTEIO"
    cur, conn = abrir_conexao_e_cursor()
    cur.execute(query)
    tam = cur.fetchall()[0]
    if tam[0] == 0:
        print("Nenhum sorteio foi feito até o momento!")
        fechar_conexao_e_cursor()
        return 0
    query = "SELECT * FROM SORTEIO"
    #cur, conn = abrir_conexao_e_cursor()
    cur.execute(query)
    sorteios = cur.fetchall()
    fechar_conexao_e_cursor()
    print("-" * 72)
    for id, data, sorteado, quant_apostas, quant_ganhadores, premio, per_bet, acumulo in sorteios:
        print("-" * 72)
        print(f" Sorteio do dia {data}:")
        print(f" Números sorteados: {sorteado}")
        print(f" Quantidade de apostas: {quant_apostas}")
        print(f" Quantidade de ganhadores: {quant_ganhadores}")
        print(f" Premio: R$ {premio}")
        print(f" Premio por ganhador: R$ {per_bet}")
        print(f" Acumulado para próximo sorteio: R$ {acumulo}")
        print("-" * 72)
    print("-" * 72)
    
# Ganhadores verifica os ganahadores, faz as rodadas, imprime lista de frequencia, premios....
def Ganhadores(tabela_nome, data):# Prestem bastante atenção na documentacao aqui que pode ser um pouco complexo
    ganhadores_data = f"ganhadores_{data}"# Formata a data para o nome da tabela de ganhadores
    # Verifica se o sorteio ja existe-----------------------------------------
    query = f"SELECT COUNT(*) FROM SORTEIO WHERE DATA = {data};" # CHECA SE SORTEIO JA EXISTE
    cur, conn = abrir_conexao_e_cursor() # Conecta ao banco de dados e retorna cursor e conexao
    cur.execute(query)
    resultado = cur.fetchall()[0]
    #print(resultado)# Debug
    fechar_conexao_e_cursor()# Fecha a conexao e o cursor
    
    # Sorteio ja existe -----------------------------------------------------------------------------------------------------------------
    if resultado[0] > 0:
        print("Sorteio ja existe")# Debug
        query_0 = f"SELECT DATA, SORTEADO, QUANT_APOSTAS, QUANT_GANHADORES, PREMIO, PER_BET, ACUMULO FROM SORTEIO WHERE DATA = {data}" # Pega os dados do sorteio
        cur, conn = abrir_conexao_e_cursor() # Conecta ao banco de dados e retorna cursor e conexao
        cur.execute(query_0)# Executa a query
        sorteio = cur.fetchall()# Pega numeros sorteados da data do sorteio
        #print(sorteio)# Debug
        id_date, drawn, quantidade_apostas, quantidade_ganhadores, price, por_aposta, accum = sorteio[0][0], sorteio[0][1], sorteio[0][2], sorteio[0][3], sorteio[0][4], sorteio[0][5], sorteio[0][6]
        fechar_conexao_e_cursor()# Fecha a conexao e o cursor
        list_sorteio = drawn.split(",")# Passa para lista
        #print(list_sorteio)# Debug
        print("Números sorteados: ", list_sorteio)
        print(f"Quantidade de rodadas: {len(list_sorteio)-5}")
        print(f"Quantidade do premio: R$ {price}")
        if quantidade_ganhadores == 0:
            print("Ninguem ganhou a aposta no ultimo sorteio!")
        else:
            print(f"Quantidade de ganhadores: {quantidade_ganhadores}")
            print(f"Quantidade do premio por ganhador: R$ {por_aposta}")
        print(f"Acumulo: R$ {accum}")
        
        # Pega a frequencia dos numeros---------------------------------------------
        query_02 = f"SELECT APOSTA FROM {tabela_nome}"# Para pegar a frequencia dos numeros
        cur, conn = abrir_conexao_e_cursor() 
        cur.execute(query_02)
        bets = cur.fetchall()
        fechar_conexao_e_cursor()
        #print(bets)# Debug 
        bet_list_str = [bet[0] for bet in bets]# Pega apostas e passa para a lista
        #print(bet_list_str)# Debug
        bet_list = [[int(num) for num in aposta.split(",")] for aposta in bet_list_str]# Passa as apostas para uma lista de listas
        #print(bet_list)# Debug
        dict_freq_numbers = defaultdict(int)# Dicionario para contar a frequencia dos numeros
        for aposta in bet_list:
            dict_aposta = Counter(aposta)# Frequencia dos numeros da aposta
            for numero in dict_aposta:
                if numero not in dict_freq_numbers:
                    dict_freq_numbers[numero] = 1
                    #print(f"Numero {numero} =1 ")
                else:
                    dict_freq_numbers[numero] += 1
                    #print(f"Numero {numero} +=1 -> {dict_freq_numbers[numero]}")
        #print(dict_freq_numbers)# Debug
        lista_sorted = sorted(dict_freq_numbers.items(), key=lambda item: item[1], reverse=True) # Ordenando os itens do dicionário por valor (frequência) em ordem decrescente
        print("-" * 18)
        print(f"|{'Núm'} | {'Frequency'} |")
        print("-" * 18)
        for numero, freq in lista_sorted:# Imprimindo a lista
            print(f"|{numero:<3} | {freq:<9} |")
            print("-" * 18)
        print("-")
        #----------------------------------------------------------------------------
        if quantidade_ganhadores > 0:# Se pelo menos uma pessoa ganhou
        # Pega os ganhadores-----------------------------------------------------
            query_01 = f"SELECT NOME, APOSTA, ID_APOSTA FROM {ganhadores_data};"# Query para pegar a apostas ganhas
            cur, conn = abrir_conexao_e_cursor() 
            cur.execute(query_01)
            ganhadores_tulpa = cur.fetchall()
            fechar_conexao_e_cursor()
            #print(ganhadores_tulpa)# Debug
            winners_list = [winner for winner in ganhadores_tulpa]# Passa ganhadores para uma lista
            print("-" * 57)
            print(f"|{'ID da aposta':<12}|{'Nome':<27}|{'Aposta':<15}|")
            print("-" * 57)
            #print(winners_list)# Debug
            for winners in winners_list:
                print(f"|{winners[0]:<12}|{winners[1]:<27}|{winners[2]:<15}|")
                print("-" * 57)
            print("-" * 57)
            print("-")
            # Apostas unicas dos ganhadores---------------------------------------------
            # Há a possibilidade tambem de fazer uma consulta
            # cur, conn = abrir_conexao_e_cursor()
            # query_02 = f"SELECT DISTINCT APOSTA FROM {ganhadores_data}" 
            # cur.execute(query_02)
            # apostas_unicas = cur.fetchall()
            # fechar_conexao_e_cursor()
            print("-" * 27)
            print("Apostas únicas ganhas".center(27, "-"))
            print("-" * 27)
            aposta_list = [winner[1] for winner in winners_list]
            distinct = set(aposta_list)# Converter a lista em um conjunto para remover duplicatas
            distinct_lista = list(distinct)# Precisa que o resultado final seja uma lista para printar
            #print(distinct_lista)# Debug
            for aposta in distinct_lista:# Printa as apostas unicas e conta a frequencia dos numeros
                print(f"|{aposta:<27}|")
            print("-" * 27)
            print("-")
            #print("fim3")# Debug
            fechar_conexao_e_cursor()# Pra garantir que a conexao feche
            return 0
    # Se o sorteio não existir ----------------------------------------------------------------------------------------------------------------
    else:
        # Verifica se tem apostas na tabela-----------------------------------------
        query = f"SELECT COUNT(*) FROM {tabela_nome}"# Query para pegar a quantidade de apostas
        cur, conn = abrir_conexao_e_cursor() # Conecta ao banco de dados e retorna cursor e conexao
        cur.execute(query)
        quantidade_apostas = cur.fetchall()[0][0]# Pega a quantidade de apostas
        fechar_conexao_e_cursor()# Fecha a conexao e o cursor
        print(f"Quantidade de apostas: {quantidade_apostas}") # Debug
        if quantidade_apostas == 0:
            print("Nenhuma aposta foi feita no dia de hoje!")
            print("-" * 72)
            return 0
        
        # Sorteio dos 5 primeiros nuemros ----------------------------------------
        sorteio = random.sample(range(1, 51), 5)# Seleciona 5 numeros aleatorios entre 1 e 50
        sorteio.sort()# Ordena
        #print(sorteio)# Debug
        freq_sorteio = Counter(sorteio)# Frequencia dos numeros
        #print(freq_sorteio)# Debug
        acum = Acumulo()# Pega o acumulo
        
        # Pega as apostas -------------------------------------------------------
        cur, conn = abrir_conexao_e_cursor() # Conecta ao banco de dados e retorna cursor e conexao
        query = f"SELECT APOSTA FROM {tabela_nome}"# Query para pegar as apostas
        cur.execute(query)# Executa a query
        rows = cur.fetchall()# Pega todas as linhas da tabela
        apostas_str=[aposta[0] for aposta in rows]# Pega o primeiro item da tulpa aposta e passa para a lista
        apostas = [[int(num) for num in aposta.split(",")] for aposta in apostas_str]# Passa as apostas para uma lista de listas
        #print(apostas_str)# Debug OK
        #print(apostas)# Debug OK  
        fechar_conexao_e_cursor()# Fecha a conexao e o cursor
        
        # Inicializa as listas --------------------------------------------------
        rodada = 0# Controle para saber em qual rodada estamos
        ganhador = -1# Controle para saber se tem ganhador
        lista_ganhadores=[]# Lista com indice das apostas ganhas
        lista_dic_aposta = []# Lista de dicionarios com a frequencia dos numeros de cada aposta
        apostas_ganhadoras = []# Lista com as apostas ganhadoras
        freq_num= defaultdict(int)# Lista com a frequencia geral dos numeros
        lista_acertos =[0] * len(apostas)# Lista com os acertos de cada ID( quanto cada aposta acertou)
        # Primeira verificacao pra ver a frequencia---------------------
        for i, aposta in enumerate(apostas):
            freq_aposta = Counter(aposta)# Frequencia dos numeros da aposta
            #print(freq_aposta)# Debug
            lista_dic_aposta.append(freq_aposta)
            #print(lista_dic_aposta)# Debug
            for numero in freq_aposta:
                #print(numero)# Debug
                if numero not in freq_num:
                    freq_num[numero] = 1# Adiciona o numero ao dicionario
                    #print(f"Numero {numero} =1 ")
                else:
                    freq_num[numero]+=1# Conta a frequencia geral dos numeros
                    #print(f"Numero {numero} +=1 -> {freq_num[numero]}")
        #Ver se tem ganhador-----------------------------------------------------
        #print(freq_sorteio)# Debug
        for i, fr_aposta in enumerate(lista_dic_aposta):
            for numero in freq_sorteio:
                if  fr_aposta[numero] == 1:
                    lista_acertos[i]+=1
                    if lista_acertos[i] == 5:
                        #print("Um ganhador!")
                        ganhador +=1
                        lista_ganhadores.append(i+1000)
                    #lista_ganhadores[ganhador] = i
        #print(lista_acertos)# Debug
        #print(freq_num)# Debug
        #Se certifica que n tem sorteio com a mesma data e se n tem insere----------------------------
        if ganhador >= 0:# Caso o haja gahador na primeira verificação(Rodada 0)
            sorteio_str = ",".join(map(str, sorteio))
            query_7 = f'''SELECT COUNT(*) FROM SORTEIO WHERE DATA = {data}'''# Query para garantir que n existem sorteio nessa data
            cur, conn = abrir_conexao_e_cursor() #Faz conexao e rotorna cursor e conexao
            cur.execute(query_7)
            resultado = cur.fetchall()[0]
            fechar_conexao_e_cursor()# Fecha a conexao e o cursor
            if resultado[0] > 0:
                print("Sorteio ja existe: Erro")
                return 0
            else:
                #print(sorteio_str)# Debug
                query_8 = f'''INSERT INTO SORTEIO(DATA, SORTEADO, QUANT_APOSTAS, QUANT_GANHADORES, PREMIO, PER_BET, ACUMULO)
                                VALUES
                                ('{data}','{sorteio_str}', {len(apostas)}, {ganhador+1}, {((4.5 * len(apostas)))}, {(((4.5 * len(apostas))+acum)/ (ganhador+1))}, 0)'''
                cur, conn = abrir_conexao_e_cursor() 
                cur.execute(query_8)
                conn.commit()
                fechar_conexao_e_cursor()
        
        # Caso ninguem tiver acertado na primeira rodada se rubmetera 
        # a escolha de mais um numero aleatorio
        while ganhador < 0 and rodada<25:# Enquanto n tiver ganhador
            while True:# Escolhe um outro numero
                new_numb = random.sample(range(1, 51), 1)# Novo sorteio
                if new_numb[0] not in sorteio:# Se o novo sorteio n for igual ao anterior
                    sorteio.append(new_numb[0])# Adiciona o novo sorteio
                    freq_sorteio[new_numb[0]] = 1# Adiciona o novo sorteio a frequencia
                    #sorteio.sort()# Ordena
                    #print(sorteio)# Debug OK
                    #print(new_numb[0])# Debug
                    break
            # Como temos uma lista de dicionario de frequencia de apostas de cada aposta, 
            # e ja temos uma lista de acertos por indice, so precisamos ver se o novo numero esta na frequencia
            # do dicionario da aposta, se sim adiciona a lista de acertos, ao final teremos uma lista de acertos 
            # que quando fechar 5 acertos teremos um ganhador. Passaremos assim o indice do ganhador para a 
            # lista de ganhadores, aumentaremos seu indice e se no final tivermos um ganhador nao iremos para
            # a proxima rodada e printaremos os ganhadores, a frequencia dos numeros 
            # e as apostas unicas dos ganhadores
            for i, f_aposta in enumerate(lista_dic_aposta):
                if f_aposta[new_numb[0]] == freq_sorteio[new_numb[0]]:
                #if f_aposta[new_numb[0]] == 1:
                    lista_acertos[i] += 1
                    #print
                    if lista_acertos[i] == 5:
                        #print("Um ganhador!")
                        ganhador +=1
                        #print(ganhador)# Debug
                        lista_ganhadores.append(i+1000)
                        #lista_ganhadores[ganhador] = i
            rodada += 1
            if ganhador >= 0:
                break
            #print(f"Rodada {rodada}") # Debug
            #print(sorteio)# Debug
            #print(lista_acertos)# Debug
            
        # print("-\n"*5)# Debug   
        # print(sorteio)# Debug
        # print("-\n"*5)# Debug  
        # Caso o haja gahador na primeira verificação(Rodada 0)--------------------------
        if ganhador >= 0:# Caso o haja gahador 
            # Pega a tabela do banco de dados--------------------------------------------
            lista_ganhadores_str = ','.join(map(str, lista_ganhadores))
            #print(lista_ganhadores_str)# Debug
            #print(lista_ganhadores)# Debug
            cur, conn = abrir_conexao_e_cursor() 
            query_2 = f"SELECT ID, NOME, CPF, APOSTA FROM {tabela_nome} WHERE ID IN ({lista_ganhadores_str}) ORDER BY NOME"# Query para pegar os dados dos ganhadores
            cur.execute(query_2)  # Usa o nome da tabela passado como argumento
            tabela = cur.fetchall()# Pega todas as linhas da tabela
            fechar_conexao_e_cursor()# Fecha a conexao e o cursor
            
            # Prints --------------------------------------------------------------------
            print("-" * 57)
            print("Números sorteados: ", sorteio)
            print(f"Quantidade de rodadas: {rodada}")
            print(f"Quantidade de ganhadores: {ganhador+1}")
            print(f"Quantidade do premio: R$ {4.5 * (len(apostas))}")
            premio_per_ganhador = (4.5 * (len(apostas))) / (ganhador+1)
            print(f"Quantidade do premio por ganhador: R$ {premio_per_ganhador + acum}")
            #----------------------------------------------------------------------------
            #Se certifica que n tem sorteio com a mesma data e se n tem, insere----------------------------
            sorteio_str = ",".join(map(str, sorteio))
            query_7 = f'''SELECT COUNT(*) FROM SORTEIO WHERE DATA = {data}'''# Query para garantir que n existem sorteio nessa data
            cur, conn = abrir_conexao_e_cursor() #Faz conexao e rotorna cursor e conexao
            cur.execute(query_7)
            resultado = cur.fetchall()[0]
            fechar_conexao_e_cursor()# Fecha a conexao e o cursor
            #Se certifica que n tem sorteio com a mesma data e se n tem, insere----------------------------
            if resultado[0] > 0:
                print("Sorteio ja existe: Erro")
                return 0
            else:
                print(sorteio_str)# Debug
                query_8 = f'''INSERT INTO SORTEIO(DATA, SORTEADO, QUANT_APOSTAS, QUANT_GANHADORES, PREMIO, PER_BET, ACUMULO)
                                VALUES
                                ('{data}','{sorteio_str}', {len(apostas)}, {ganhador+1}, {(4.5 * len(apostas))}, {(((4.5 * len(apostas))+acum)/ (ganhador+1))}, 0)'''
                cur, conn = abrir_conexao_e_cursor() 
                cur.execute(query_8)
                conn.commit()
                fechar_conexao_e_cursor()
            #----------------------------------------------------------------------------
            # Printa o(s) ganhador(es) em ordem alfabética------------------------------
            # Cria tabela de ganhadores do respectivo sorteio---------------------------
            query_3 = f''' CREATE TABLE IF NOT EXISTS {ganhadores_data}(
                    ID SERIAL PRIMARY KEY,
                    NOME VARCHAR(72),
                    APOSTA VARCHAR(18),
                    ID_APOSTA INT REFERENCES {tabela_nome}(ID)
            )
            '''# 
            cur, conn = abrir_conexao_e_cursor() #Faz conexao e rotorna cursor e conexao
            cur.execute(query_3)# Cria a tabela de ganhadores
            conn.commit()# Salva as alterações no banco de dados
            fechar_conexao_e_cursor()# Fecha a conexao e o cursor
            #----------------------------------------------------------------------------
            print("-" * 57)
            print("Lista de Ganhadores ".center(57, "-"))
            print("-" * 57)
            print(f"|{'ID da aposta':<12}|{'Nome':<27}|{'Aposta':<15}|")
            print("-" * 57)
            #print(ganhadores_data)# Debug
            #print(len(tabela))
            cur, conn = abrir_conexao_e_cursor() #Faz conexao e rotorna cursor e conexao
            for ID, NOME, CPF, APOSTA in tabela:# Pega os dados do ganhador
                query_4 = f'''INSERT INTO {ganhadores_data}(NOME, APOSTA, ID_APOSTA)
                          VALUES
                          ('{NOME}', '{APOSTA}', {ID})
                '''
                print(f"|{ID:<12}|{NOME:<27}|{APOSTA:<15}|")
                print("-" * 57)
                apostas_ganhadoras.append(APOSTA)# Adiciona a aposta na lista de apostas ganhadoras
                cur.execute(query_4)# Insere a aposta na tabela de ganhadores
            conn.commit()# Salva as alterações no banco de dados            
            fechar_conexao_e_cursor()# Fecha a conexao e o cursor
            
            # Apostas unicas dos ganhadores---------------------------------------------
            print(" "+"-" * 27)
            print(" "+"Lista de apostas únicas".center(27, "-"))
            print(" "+"ganhas".center(27, "-"))
            print(" "+"-" * 27)
            apostas_unicas = set(apostas_ganhadoras)# Converter a lista em um conjunto para remover duplicatas
            apostas_unicas_lista = list(apostas_unicas)# Precisa que o resultado final seja uma lista para printar
            for aposta in apostas_unicas_lista:# Printa as apostas unicas
                print(f"|{aposta:<27}|")
                print(" "+"-" * 27)
            print(" "+"-" * 27)
            # Printa a frequencia dos numeros-------------------------------------------
            # Ordenando os itens do dicionário por valor (frequência) em ordem decrescente
            lista_ordenada = sorted(freq_num.items(), key=lambda item: item[1], reverse=True)
            print("-" * 18)
            print(f"|{'Núm'} | {'Frequency'} |")
            print("-" * 18)
            for numero, freq in lista_ordenada:# Imprimindo a lista
                print(f"|{numero:<3} | {freq:<9} |")
                print("-" * 18)
            print("-" * 18)
            #fechar_conexao_e_cursor()# Fecha a conexao e o cursor
        
        else:# Caso n tenha ganhador e tenha passado 25 rodadas--------------------------
            #Se certifica que n tem sorteio com a mesma data e se n tem, insere----------------------------
            sorteio_str = ",".join(map(str, sorteio))
            query_7 = f'''SELECT COUNT(*) FROM SORTEIO WHERE DATA = {data}'''# Query para garantir que n existem sorteio nessa data
            cur, conn = abrir_conexao_e_cursor() #Faz conexao e rotorna cursor e conexao
            cur.execute(query_7)
            resultado = cur.fetchall()[0]
            fechar_conexao_e_cursor()# Fecha a conexao e o cursor
            if resultado[0] > 0:
                print("Sorteio ja existe: Erro")
                return 0 
            else:
                print(len(sorteio_str))
                print(sorteio_str)# Debug
                query_8 = f'''INSERT INTO SORTEIO(DATA, SORTEADO, QUANT_APOSTAS, QUANT_GANHADORES, PREMIO, PER_BET, ACUMULO)
                                VALUES
                                ('{data}','{sorteio_str}', {len(apostas)}, 0, {(4.5 * len(apostas))}, 0, {(4.5 * len(apostas))+acum})'''
                cur, conn = abrir_conexao_e_cursor() 
                cur.execute(query_8)
                conn.commit()
                fechar_conexao_e_cursor()
            print(f"Ninguem ganhou! Premio acumulado para o proximo sorteio R$:{4.5 * (len(apostas))}")  
            #fechar_conexao_e_cursor()# Fecha a conexao e o cursor (pra garantir) 
            #print("fim1")# Debug
            fechar_conexao_e_cursor()# Pra garantir que a conexao feche
            return 0
        
    # print("fim0")# Debug
    fechar_conexao_e_cursor()# Pra garantir que a conexao feche
    return 0
      
def valida_cpf(cpf):# Função para validar o CPF
    if len(cpf) != 11 or len(set(cpf)) == 1:# Verifica se o CPF tem 11 dígitos ou se todos os dígitos são iguais
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))# Calcula o primeiro dígito verificador
    resto = soma % 11
    digito1 = '0' if resto < 2 else str(11 - resto)
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))# Calcula o segundo dígito verificador
    resto = soma % 11
    digito2 = '0' if resto < 2 else str(11 - resto)
    return digito1 == cpf[9] and digito2 == cpf[10]# Verifica se os dígitos calculados são iguais aos informados
    
def aposta(tabela_nome):# Função para pegar dados e fazer uma aposta
    apostas = []# Lista para armazenar as apostas, de um mesmo usuário, em uma única sessão
    # Pega os dados do apostador--------------------------------
    # Nome, sobrenome, cpf---------------------------------------------------------------------------------------------------------
    while True:# Loop para ganrantir exigencias
        # Nome do apostador com letras e no mínimo 3 caracteres
        print("Digite primeiro nome, com pelo menos 3 letras(Somente letras): ")
        while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
            x = ininput() 
            if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                print("Sentimos, mas o sorteio começará agora!")
                return 0
            if isinstance(x, str):
                break
        nome = x
        if len(nome) >= 3 and nome.isalpha():
            break
        else:
            print("Nome inválido\n-")
    while True:# Loop para ganrantir exigencias
        # Sobrenome do apostador com letras e no mínimo 3 caracteres
        print("Digite seu sobrenome, com pelo menos 3 letras(Somente letras): ")
        while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
            x = ininput() 
            if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                print("Sentimos, mas o sorteio começará agora!")
                return 0
            if isinstance(x, str):
                break
        sobrenome = x
        if len(sobrenome) >= 3 and sobrenome.isalpha():
            break
        else:
            print("Sobrenome inválido\n-")
    while True:# Loop para ganrantir exigencias
        # Confere se o CPF é válido de acordo com equacao de cpf valido
        print("Digite o CPF, com 11 dígitos: ")
        while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
            x = ininput() 
            if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                print("Sentimos, mas o sorteio começará agora!")
                return 0
            if isinstance(x, str):
                break
        cpf = x
        if valida_cpf(cpf):
            break
        else:
            print("CPF inválido\n-")
    #------------------------------------------------------------------------------------------------------------------------------
    
    # Formata -----------------------------------------------
    # Nome e sobrenome para Nome_Completo------------------------------------------------------------------------------------------
    nome = nome.rstrip()# Tira os espacos em branco do nome
    sobrenome = sobrenome.rstrip()# Tira os espacos em branco do sobrenome
    if len(nome) > 36:# Se o nome for maior que 36 caracteres, split 
        nome = nome[:36]
    if len(sobrenome) > 36:# Se o sobrenome for maior que 36 caracteres, split
        sobrenome = sobrenome[:36]
    nome_completo = nome + " " + sobrenome # Junta o nome e sobrenome
    nome_completo = nome_completo.upper()# Upper Case nome para ficar mais bonito na tabela, para manter uma certa concistencia
    #------------------------------------------------------------------------------------------------------------------------------
    # Pega a primeira aposta-----------------------------
    # Passa o nome_completo, cpf e tabela_nome para a função permitir que possa fazer mais apostas sem ficar pondo os dados novamente
    x = pega_aposta(nome_completo, cpf, tabela_nome)
    #------------------------------------------------------------------------------------------------------------------------------
    
    if x == 0:# Se x for 0, a aposta foi cancelada pelo pega_aposta
        print("Aposta cancelada\n-")
        print("Tenha um bom dia!\n-")
        return 0# Volta ao menu
    apostas.append(x)# Se x !=0 quer dizer que a aposta foi concluida e inserida no banco de dados, adiciona  então a aposta na lista de apostas
    while True:# Pede a opcao até ser uma opcao valida
        #-------------------Mini Menu--------------------------
        print("Deseja fazer mais uma aposta ou terminar?")
        print("1 - Mais uma aposta")
        print("2 - Terminar")
        while True:
            try:
                print("-> ")
                while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                    x = ininput() 
                    if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                        print("Sentimos, mas as apostas estão fechadas no momento.")
                        return 0
                    if isinstance(x, str):
                        break
                op = int(x)
                break
            except ValueError:
                print("Opção invalida!\n-")
        print("-")
        #-------------------------------------------------------
        if op == 1:# Se o usuario deseja fazer mais uma aposta chama a funcao pega_aposta novamente
            x = pega_aposta(nome_completo, cpf, tabela_nome)
            if x == 0:# O user cancelou, pois mudou de ideia no meio do caminho...
                # Confere quantas apostas foram feitas pelo user
                if len(apostas) <= 0:# Caso algum erro(mas n é executar aqui nunca)
                    #Se mais nenhuma aposta foi feita, volta ao menu inicial
                    print("Aposta cancelada\n-")
                    print("Tenha um bom dia!\n-")
                else:# User mudou de ideia, nao quer mais apostar, e tem apostas em seu nome
                    print(f"|{len(apostas)}| Apostas realizadas com sucesso!\n-")
                    print("Suas apostas foram: ")
                    for i, x in enumerate(apostas):# Prinra as apostas feitas pelo usuario
                        print(f"{i+1}º aposta: {x}")
                    print("Tenha um bom dia!")
                    print(("-\n" * 3)[:-1])
                return 0
            else:
                # Se o ususario nao mudou de ideia no meio da aposta, e a finalizou, 
                #adiciona a aposta na lista de apostas
                apostas.append(x)
        elif op == 2:# Usuario deseja terminar
            print("Apostas realizadas com sucesso!\n-")
            print("Suas apostas foram: ")
            for i, x in enumerate(apostas):# Prinra as apostas feitas pelo usuario
                print(f"{i+1}º aposta: {x}")
            print("O valor totla das apostas é R$:", len(apostas) * 4.5)
            print("Tenha um bom dia!")
            print(("-\n" * 3)[:-1])
            return 0# Volta ao menu inicial
        else:
            print("Opção inválida\n-")# Caso o usuario insira uma opcao invalida pede de novo a opcao

def pega_aposta(nome_completo, cpf, tabela_nome): # Pega a aposta para um mesmo user
    #global where_it_is  
    # Mini Menu --------------------------------------------------------------------------
    print("-\nVoce deseja inserir os numeros ou prefere que o sistema escolha para voce?")
    print("1 - Inserir numeros")
    print("2 - Sistema escolhe")
    #---------------------------------------------------------------------------------------
    lista = [] # Lista para armazenar os números da aposta
    
    while True: # Loop para garantir que o usuário insira uma opção válida
        try:
            print("Digite a opção desejada: ")
            while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                x = ininput() 
                if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                    print("Sentimos, mas o sorteio começará agora!")
                    return 0
                if isinstance(x, str):
                    break
            op = int(x)
            if op == 1:# Usuario insere os numeros
                print("Digite 5 numeros entre 1 e 50\n-")
                for i in range(5):
                    while True:# Garante que os numeros sejam unicos e entre 1 e 50
                        try:    
                            print(f"{i+1}º número: ")
                            while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
                                x = ininput() 
                                if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                                    print("Sentimos, mas as apostas estão fechadas no momento.")
                                    return 0
                                if isinstance(x, str):
                                    break
                            n = int(x)# Pega o numero e informa user
                            if 1 <= n < 51 and n not in lista:  # Verifica se o número está no intervalo e é único
                                lista.append(n)
                                break # Sai do loop interno se um número válido for inserido
                            else:
                                print("Número inválido ou repetido. Por favor, insira um número único entre 1 e 50.\n-")
                        except ValueError:
                            print("Opção número invalido!\n-")
                if len(lista) == 5:
                    break
            elif op == 2:# Sistema escolhe os numeros
                lista = random.sample(range(1, 51), 5)
                break
            else:
                print("Opção invalida!\n-")
        except ValueError:
            print("Opção invalida!\n-")

    lista.sort()# Ordena a lista 
    numeros = ",".join(map(str, lista))# Passa para string e separa por virgula, para ser mais facil de ver a frequencia dos numeros depois com Counter
    print(f"-\nOs numeros escolhidos foram: {lista}\n-")# Printa a aposta para informar o user
    
    try:# Confirma a aposta ou cancela a aposta
        print("Para confirmar a aposta digite 1,\nou digite qualquer tecla para cancelar\n(MENOS O BOTÃO POWER DO PC!):")
        while True:# Pega na lista até ter um valor, se sair do horario de apostas retorna True e reinicia o menu
            x = ininput() 
            if isinstance(x, bool):# Se estiver aqui e não for pra estar aqui
                print("Sentimos, mas as apostas estão fechadas no momento.")
                return 0
            if isinstance(x, str):
                break
        op = int(x)
        print("-")
        #cpf_numb = int(cpf)
        #print(f"'{nome_completo}', '{cpf_numb}', '{numeros}' ")# Debug
        
        if op == 1:# Como o user quer seguir enfrente insere a aposta no banco de dados
            cur, conn = abrir_conexao_e_cursor()# Pega o cursor e a conexao
            # Insere a aposta no banco de dados
            # As apostas sao inseridas conforme o usuario decide fazer uma nova aposta, assim se der algum erro no meio garante que a aposta foi inserida garantindo a atomicidade da transacao
            query = f'''INSERT INTO {tabela_nome}(NOME, CPF, APOSTA, HORA_DA_APOSTA) 
                       VALUES
                       ('{nome_completo}', '{cpf}', '{numeros}', CURRENT_TIMESTAMP);'''# Query para inserir a aposta
            cur.execute(query)
            conn.commit()# Commit salva no banco de dados
            fechar_conexao_e_cursor()
            print("Aposta:")# Formatacao bonitinha
            print("-" * 54)
            print(f"{'Nome Completo':<21} | {'CPF':<12} | {'APOSTA':<15}")
            print("-" * 54)
            print(f"{nome_completo:<21} | {cpf:<12} | {numeros:<15} ")
            print("-" * 54)
            print("Realizada com sucesso!")
            print(("-\n" * 2)[:-1])
            return lista # Retorna a lista(aposta) siguinificando que o user terminou a aposta e n deu pra tras-> volta para aposta()
        print("Aposta cancelada")# Caso deu pra tras cancela e retorna zero -> volta para aposta()
        print(("-\n" * 3)[:-1])
        return 0 #-> volta para aposta()
    
    except ValueError: # Caso erro o sistema indentifica que o user n seguiu e para questoes de seguranca cancela a operacao
        print("Aposta cancelada")
        print(("-\n" * 3)[:-1])
        return 0  #-> volta para aposta()  
    
def verificar_aposta(tabela_nome):# Printa as informacoes da tabela no banco de dados de todas as apostas feitas no dia(Nome, aposta)
    cur, conn = abrir_conexao_e_cursor() #Faz conexao e rotorna cursor e conexao
    query = f"SELECT ID, NOME, CPF, APOSTA FROM {tabela_nome}"# Query para pegar as apostas
    cur.execute(query)  # Usa o nome da tabela passado como argumento
    # Supondo que o código para processar e exibir os resultados das apostas esteja aqui
    rows = cur.fetchall()# Pega todas as linhas da tabela
    fechar_conexao_e_cursor()# Fecha a conexão atual se estiver aberta
    print("-" * 54)
    print(f"{'ID da aposta':<12} | {'Nome':<20} |{'Aposta':<15}")
    print("-" * 54) 
    
    for id_aposta, nome, _, numeros_aposta in rows:  # Desestruturação da tupla 'row'
        print(f"|{id_aposta:<12} | {nome:<20} |{numeros_aposta:<15}|")
        print("-" * 54)
    
    print(("-\n" * 3)[:-1])

def SQL_INSERTION(tabela_nome, MAX):  # Insere dados na tabela | MAX é a quantidade de apostas que serão feitas
    apostas_unicas = set()# Registro das apostas únicas
    cpf = "12345678901"# CPF padrão para as apostas aleatórias
    while len(apostas_unicas) < MAX:# Combinações aleatórias únicas até atingir o total desejado
        aposta_aleatoria = random.sample(range(1, 51), 5)# Gera aposta aleatória
        aposta_aleatoria_str = ','.join(map(str, sorted(aposta_aleatoria)))# Formata para passar para aposta na tabela
        apostas_unicas.add(aposta_aleatoria_str)# Adiciona a aposta formatada ao conjunto apostas_únicas, se ainda não existir
    cur, conn = abrir_conexao_e_cursor()
    for aposta in apostas_unicas:# Insere cada aposta na tabela
        #cur, conn = abrir_conexao_e_cursor()
        query = f"INSERT INTO {tabela_nome}(NOME, CPF, APOSTA, HORA_DA_APOSTA) VALUES ('XXX XXX', '{cpf}', '{aposta}', CURRENT_TIMESTAMP);"
        cur.execute(query)
        #conn.commit()  
        #fechar_conexao_e_cursor() 
    conn.commit()    
    fechar_conexao_e_cursor() 
    print(f"{MAX} apostas aleatórias inseridas com sucesso!\n-")  # Debug
    print("-" * 54)
    
def main():
    global senha_adm # Pega a senha do admin e inicia o programa
    #global INICIO, FIM, hora
    
    thread = threading.Thread(target=thread_atualiza_tempo)# Inicia a thread para o acumulo
    thread.daemon = True# Garante que a thread morra quando o programa morrer
    thread.start()# começa a thread
    
    print("-" * 72)
    print("-" * 72) #8<14<14 14>=14 ou 14<8 ta(ok)
    print("Bem-vindo ao sistema de apostas da Dell IT ACADEMY!".center(72, "-"))
    if (INICIO <= hora < FIM):# Caso o programa seja iniciado no horario entre as 8 e 20 horas
        print("Sistema de apostas inaugura Agora!".center(72, "-"))
    elif (hora >= FIM):# Caso o programa seja iniciado no horario entre as 20 e 00:00 horas
        print("Sistema de apostas inaugura amanhã às 8:00".center(72, "-"))
    elif (hora < INICIO):# Caso o programa seja iniciado no horario entre as 00:00 e 8 horas
        print("Sistema de apostas inaugura às 8:00".center(72, "-"))
    print("-" * 72)
    print("-" * 72)
        
    while True:
        try:
            senha_adm = input("Digite uma senha para depois acessar\nfunções de teste e +(Tamanho 2): ")
            print("-")
            if len(senha_adm) == 2:
                print(f"Senha admin:'{senha_adm}'\n-")
                break
            else:
                print("Senha de tamanho invalido\n-")
                
        except ValueError:
            print("Valor inválido. Por favor, digite um número inteiro.")        
                    
        except KeyboardInterrupt:# Caso o usuario aperte ctrl+c
            print("")
            print(("-\n" * 6)[:-1])
            print("Muito obrigado por usar nosso programa! Realizando limpeza e saindo\n-\n-\n-")
            fechar_conexao_e_cursor() # Fecha a conexão atual se estiver aberta
            sys.exit()
    # Cria a tabela se, nao existe, SORTEIO que mantera um registro de todos os sorteios feitos
    # ---------------------------------------------------------- Escolha dos tipos de variavel:------------------------------------------------------------------------------------------------|
    # ID SERIAL PRIMARY KEY,        -> SERIAL pois nao precisa de incercao é tipico para Primari Key  
    # SORTEADO VARCHAR(81),         -> Valor sorteado sera varchar codificado em string pois pra facilitar a leitura e a manipulacao dos dados  
    # QUANT_APOSTAS                 -> Quantidade de apostas feitas no dia
    # QUANT_GANHADORES              -> Quantidade de apostas ganhadoras
    # PREMIO                        -> TIMESTAMP para registrar a hora da aposta
    # PER_BET                       -> Quantidade de valor que cada ganhador ira receber
    # ACUMULO                       -> Caso ninguem ganhe o premio acumula para o proximo sorteio
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    # Tabela SORTEIO conterá todas as anteriores numeros sorteados
    # Cria a tabela do SORTEIO------------------------------------------------
    query_9 = '''CREATE TABLE IF NOT EXISTS SORTEIO(
            ID SERIAL PRIMARY KEY,
            DATA INT NOT NULL,
            SORTEADO VARCHAR(93) NOT NULL,
            QUANT_APOSTAS INT NOT NULL,
            QUANT_GANHADORES INT NOT NULL,
            PREMIO FLOAT NOT NULL,
            PER_BET FLOAT NOT NULL,
            ACUMULO FLOAT NOT NULL
            )''' 
    cur, conn = abrir_conexao_e_cursor() # Conecta ao banco de dados e retorna cursor e conexao
    cur.execute(query_9)
    conn.commit()# Salva as alterações no banco de dados
    fechar_conexao_e_cursor()
    # Inicia a thread de input
    input_thread = threading.Thread(target=input_t)
    input_thread.daemon = True
    input_thread.start()
    #Acumulo()
    # Roda o menu principal
    while True:
        try:# Tenta rodar o programa
            menu()
        except KeyboardInterrupt:# Caso o usuario aperte ctrl+c
            print("")
            print(("-\n" * 6)[:-1])
            print("Muito obrigado por usar nosso programa! Realizando limpeza e saindo\n-\n-\n-")
            fechar_conexao_e_cursor() # Fecha a conexão atual se estiver aberta
            sys.exit()

if __name__ == "__main__":
    main()

