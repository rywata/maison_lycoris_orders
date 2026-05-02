import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client
import pandas as pd
from datetime import datetime
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# --- CONEXÃO GOOGLE SHEETS ---
google_info = st.secrets["google_creds"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_info, scope)
gc = gspread.authorize(creds)
planilha = gc.open("Controle")

# --- CONEXÃO SUPABASE ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["service_role_key"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def limpar_numerico(valor):
    if valor is None or valor == "":
        return 0.0
    s = str(valor).replace("R$", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

def limpar_data(valor, formato="%Y-%m-%d"):
    if not valor or valor == "":
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(str(valor), fmt).strftime(formato)
        except ValueError:
            continue
    return None

# --- MIGRAR MOVIMENTAÇÕES ---
print("Migrando Movimentações...")
aba = planilha.worksheet("Movimentações")
dados = aba.get_all_records()
for row in dados:
    if not row.get("ID Mov."):
        continue
    sb.table("movimentacoes").upsert({
        "id_mov": str(row["ID Mov."]),
        "data_mov": limpar_data(row.get("Data Mov."), "%Y-%m-%d %H:%M:%S"),
        "tipo": row.get("Tipo", ""),
        "item": row.get("Item", ""),
        "quantidade": limpar_numerico(row.get("Quantidade")),
        "unidade_medida": row.get("Unidade de Medida", ""),
        "unidade_compra": row.get("Unidade de Compra", ""),
        "validade": limpar_data(row.get("Validade")),
        "lote": row.get("Lote", ""),
        "custo_unitario": limpar_numerico(row.get("Custo Unitário")),
        "custo_total": limpar_numerico(row.get("Custo Total")),
    }).execute()
print(f"  {len(dados)} registros migrados.")

# --- MIGRAR PEDIDOS ---
print("Migrando Pedidos...")
aba = planilha.worksheet("Pedidos")
dados = aba.get_all_records()
rows = []
for row in dados:
    rows.append({
        "id_pedido": str(row.get("ID Pedido", "")),
        "nome_cliente": row.get("Nome Cliente", ""),
        "data_entrega": limpar_data(row.get("Data Entrega")),
        "produto": row.get("Produto", ""),
        "quantidade": int(limpar_numerico(row.get("Quantidade", 0))),
        "total_bruto": limpar_numerico(row.get("Total Bruto")),
        "desconto": limpar_numerico(row.get("Desconto")),
        "total_liquido": limpar_numerico(row.get("Total Item Líquido")),
        "data_pedido": limpar_data(row.get("Data Pedido"), "%Y-%m-%d %H:%M:%S"),
    })
if rows:
    sb.table("pedidos").insert(rows).execute()
print(f"  {len(rows)} registros migrados.")

# --- MIGRAR PRODUÇÃO ---
print("Migrando Produção...")
aba = planilha.worksheet("Produção")
dados = aba.get_all_records()
for row in dados:
    if not row.get("ID Produção"):
        continue
    sb.table("producao").upsert({
        "id_producao": str(row["ID Produção"]),
        "id_pedido": str(row.get("ID Pedido", "")),
        "data_producao": limpar_data(row.get("Data Produção"), "%Y-%m-%d %H:%M:%S"),
        "produto": row.get("Produto", ""),
        "quantidade": int(limpar_numerico(row.get("Quantidade", 0))),
        "data_entrega": limpar_data(row.get("Data Entrega")),
        "status": row.get("Status", "Pendente"),
    }).execute()
print(f"  {len(dados)} registros migrados.")

# --- MIGRAR CADASTRO DE INSUMOS ---
print("Migrando Cadastro de Insumos...")
aba = planilha.worksheet("Cadastro de Insumos")
dados = aba.get_all_records()
for row in dados:
    if not row.get("Item"):
        continue
    sb.table("cadastro_insumos").upsert({
        "item": row["Item"],
        "unidade_compra": row.get("Unidade Compra", ""),
        "unidade_receita": row.get("Unidade Receita", ""),
        "fator_conversao": limpar_numerico(row.get("Fator Conversão", 1)),
        "estoque_minimo": limpar_numerico(row.get("Estoque Mínimo", 0)),
    }).execute()
print(f"  {len(dados)} registros migrados.")

# --- MIGRAR PREÇO INSUMOS ---
print("Migrando Preço Insumos...")
aba = planilha.worksheet("Preço Insumos")
dados = aba.get_all_records(value_render_option='UNFORMATTED_VALUE')
for row in dados:
    if not row.get("Item"):
        continue
    sb.table("preco_insumos").upsert({
        "item": row["Item"],
        "preco": limpar_numerico(row.get("Preço", 0)),
        "unidade": limpar_numerico(row.get("Unidade", 1)),
        "marca": row.get("Marca", ""),
    }).execute()
print(f"  {len(dados)} registros migrados.")

# --- MIGRAR RECEITAS ---
print("Migrando Receitas...")
aba = planilha.worksheet("Receitas Python")
dados = aba.get_all_records()
rows = []
for row in dados:
    if not row.get("Produto"):
        continue
    rows.append({
        "produto": row["Produto"],
        "item_insumo": row.get("Item (Insumo)", ""),
        "qtd_receita": limpar_numerico(row.get("Qtd_Receita", 0)),
        "unidade": row.get("Unidade", ""),
    })
if rows:
    sb.table("receitas").insert(rows).execute()
print(f"  {len(rows)} registros migrados.")

print("\n✅ Migração concluída!")