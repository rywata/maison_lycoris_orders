# 🍞 Loaf Lab - Sistema Integrado de Gestão e Business Intelligence

Este repositório contém o sistema inteligente de gestão de inventário, vendas e análise financeira da **Loaf Lab**. A plataforma integra a captura de dados operacionais na ponta com um pipeline analítico robusto para tomada de decisões estratégicas de precificação, margem e CMV.

## 📐 Arquitetura do Sistema

O ecossistema é dividido em três camadas principais:
1. **Frontend & Operação (Streamlit/Python):** Interface onde são registrados os pedidos (vendas) e as movimentações de estoque/insumos.
2. **Banco de Dados & Engenharia (Supabase/PostgreSQL):** Camada de persistência e processamento pesado. Utiliza views otimizadas para consolidar regras de negócio financeiras sem sobrecarregar a aplicação.
3. **Visualização & BI (Looker Studio):** Dashboard gerencial em modo escuro para monitoramento de metas, markup, ticket médio e eficiência de produtos.

---

## 💾 Estrutura do Banco de Dados (PostgreSQL)

O sistema baseia-se em duas tabelas operacionais principais e uma View analítica estruturada:

### Tabelas Principais
* `pedidos`: Registra as vendas contendo o produto, quantidade, custos agregados e o `total_liquido`.
* `movimentacoes`: Registra a entrada de insumos, custos unitários e ordens de produção (`tipo_movimentacao = 'ENT-P'`).

### Camada Analítica: View de Margem de Contribuição
Para evitar o uso de *Data Blending* lento no Looker Studio, toda a lógica de agregação foi centralizada na View `vw_margem_contribuicao_produtos`. Ela calcula dinamicamente:
* **Margem de Contribuição Absoluta e Percentual**
* **CMV % (Custo de Mercadoria Vendida)**
* **Ticket Médio por Produto**
* **Markup Praticado**
