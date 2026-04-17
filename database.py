import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

class Database:
    def __init__(self, credentials_path=None):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        if credentials_path:
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, self.scope)
        else:
            info = dict(st.secrets["gcp_service_account"])
            raw_key = info["private_key"].strip()
            lines = [line.strip() for line in raw_key.split('\n')]
            info["private_key"] = '\n'.join(lines).replace("\\n", "\n")
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(info, self.scope)
            
        self.client = gspread.authorize(self.creds)

    def conectar_aba(self, nome_planilha, nome_aba):
        return self.client.open(nome_planilha).worksheet(nome_aba)

def salvar_pedido(aba, dados):
    try:
        aba.append_rows(dados, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False
