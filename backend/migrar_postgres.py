import psycopg
from datetime import datetime

conexao_config = {
    "dbname": "sentinela_db", "user": "sentinela", "password": "sentinela", "host": "localhost", "port":"5433"
}

try:
    with psycopg.connect(**conexao_config) as conn:
        with conn.cursor() as cursor:
            
            data_ocorrencia = datetime.fromisoformat("2026-09-05T14:30:45")
            
            

            # Query com placeholders %s
            """
            query_insert = 'INSERT INTO "Superintendencias_Ceara" (nome) \
                            VALUES (%s);'
            
            dados_cliente = ('Fortaleza',)
            cursor.execute(query_insert, dados_cliente)
            dados_cliente = ('Sertão Central',)
            cursor.execute(query_insert, dados_cliente)

            conn.commit()
            print("Superintendencias inseridas com sucesso!")

            
            query_insert = 'INSERT INTO "COADS" (coads, fk_superintendencia) \
                            VALUES (%s, %s);'

            dados_cliente = ('Fortaleza', 1)
            cursor.execute(query_insert, dados_cliente)
            dados_cliente = ('Caucaia', 1)
            cursor.execute(query_insert, dados_cliente)
            dados_cliente = ('Tauá', 2)
            cursor.execute(query_insert, dados_cliente)

            conn.commit()
            print("COADS inseridas com sucesso!")

            query_insert = 'INSERT INTO "Municipios" (municipio, fk_coads) \
                            VALUES (%s, %s);'

            dados_cliente = ('Fortaleza', 1)
            cursor.execute(query_insert, dados_cliente)
            dados_cliente = ('Caucaia', 2)
            cursor.execute(query_insert, dados_cliente)
            dados_cliente = ('Tauá', 3)
            cursor.execute(query_insert, dados_cliente) 

            conn.commit()
            print("Muinicipios inseridos com sucesso!")

            query_delete = 'DELETE FROM "Superintendencias_Ceara" \
                            WHERE id >= 6;'

            cursor.execute(query_delete)
            """

            query_insert = 'INSERT INTO "Notificaçoes" (nome, tipo_evento, categoria, data_envio, data_ocorrencia, pessoas_animais_infectados_afetados, \
                            local_ocorrencia, estado, municipio, continuidade_situacao, descricao, acs_ace_id,  \
                            status, rascunho, verificada) \
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);'
            
            dados_cliente = ('Influenza - Guararapes', 'DOENÇA', 'Doença Respiratório', datetime.now(), data_ocorrencia, 100, 'Shopping', 'Ceará', 'Fortaleza', 'Não sei', 
                             'Vários casos de influenza confirmados na região de guararapes', 2, 'PENDENTE', False, False)
            cursor.execute(query_insert, dados_cliente)
            
            """
            query_insert = 'INSERT INTO "Dados_UBS" (nome, municipio, estado) \
                            VALUES (%s, %s, %s)'
                            
            dados_insert = ('ALFONSO DE MEDEIROS', 'Fortaleza', 'Ceará')
            
            cursor.execute(query_insert, dados_insert)"""

            
            
            #query_delete = 'TRUNCATE TABLE "Superintendencias_Ceara" RESTART IDENTITY CASCADE'
            
            #cursor.execute(query_delete)

            # CRÍTICO: Confirma a transação no banco de dados
            #conn.commit()
            #print("Registro inserido com sucesso!")

except Exception as error:
    print(f"Erro ao inserir dados: {error}")
    if 'conn' in locals():
        conn.rollback() # Cancela a operação em caso de erro
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
