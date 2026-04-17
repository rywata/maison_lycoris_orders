import gspread
from oauth2client.service_account import ServiceAccountCredentials

class Database:
    def __init__(self, credentials_path):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, self.scope)
        self.client = gspread.authorize(self.creds)

    def conectar_aba(self, nome_planilha, nome_aba):
        return self.client.open(nome_planilha).worksheet(nome_aba)

def salvar_pedido(aba, dados):
    try:
        aba.append_rows(dados, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return False