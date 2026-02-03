import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import urllib.parse

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS (Sua base original)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .titulo-planilha { 
        color: #1e3a8a; 
        font-weight: bold; 
        border-bottom: 2px solid #1e3a8a; 
        margin-bottom: 20px; 
        text-align: center;
    }
    .resultado-box { 
        background-color: #262730; 
        padding: 25px; 
        border-radius: 15px; 
        border-left: 10px solid #1e3a8a; 
        box-shadow: 2px 2px 15px rgba(0,0,0,0.3); 
        color: white; 
    }
    .resultado-box h1, .resultado-box h2, .resultado-box p, .resultado-box b { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIALIZAÇÃO DO ESTADO ---
if "n_itens" not in st.session_state:
    st.session_state.n_itens = 1
if "carrinho_orc" not in st.session_state:
    st.session_state.carrinho_orc = []

# --- FUNÇÕES DE DADOS ---
def carregar_ingredientes():
    try:
        df = conn.read(worksheet="Ingredientes", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome', 'unidade', 'preco'])
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas_nuvem():
    try:
        df = conn.read(worksheet="Receitas", ttl=0)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def carregar_historico():
    try:
        df = conn.read(worksheet="Orcamentos_Salvos", ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame(columns=['Data', 'Cliente', 'Pedido', 'Itens', 'Valor_Final'])

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- SIDEBAR: AJUSTE DE TAXAS (MANTIDO) ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        st.divider()
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    # --- CONFIGURAÇÕES DO PRODUTO (BASE ORIGINAL) ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final (Para Receita):", key="nome_prod_receita")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=135)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])

    # (Lógica de montagem de receita/ingredientes omitida aqui para focar no orçamento, mas mantida no seu sistema)
    # ... código de ingredientes da receita ...

    # =========================================================
    # --- NOVO GERADOR DE ORÇAMENTOS (CONFORME SOLICITADO) ---
    # =========================================================
    st.divider()
    st.markdown("<h2 class='titulo-planilha'>📝 Gerador de Orçamentos Profissional</h2>", unsafe_allow_html=True)
    
    tab_orc, tab_salvos = st.tabs(["🆕 Criar Orçamento", "📂 Orçamentos Salvos"])

    with tab_orc:
        # 1. Cadastro do Orçamento
        c_orc1, c_orc2, c_orc3 = st.columns([2, 1, 1])
        nome_cliente = c_orc1.text_input("👤 Nome do Cliente")
        tel_cliente = c_orc2.text_input("📞 Telefone (WhatsApp)")
        data_orc = c_orc3.date_input("📅 Data", value=date.today())
        
        grupo_pedido = st.text_input("🎁 Nome do Grupo/Pedido", placeholder="Ex: Kit Festa Trufado")

        st.markdown("#### 🛒 Adicionar Itens da Planilha")
        col_item1, col_item2, col_item3, col_item4 = st.columns([3, 1, 1, 1])
        
        with col_item1:
            item_lista = st.selectbox("Selecione o Item (Ingrediente):", options=[""] + df_ing['nome'].tolist(), key="sel_item_orc")
        with col_item2:
            qtd_item_orc = st.number_input("Qtd", min_value=1, value=1, key="q_item_orc")
        with col_item3:
            f_item_orc = st.number_input("Frete/Item (R$)", value=0.0)
        with col_item4:
            e_item_orc = st.number_input("Emb/Item (R$)", value=0.0)

        if st.button("➕ Adicionar ao Orçamento"):
            if item_lista != "":
                # Busca automática do custo unitário puro na planilha
                custo_puro = float(df_ing[df_ing['nome'] == item_lista]['preco'].iloc[0])
                st.session_state.carrinho_orc.append({
                    "nome": item_lista,
                    "qtd": qtd_item_orc,
                    "custo_unit": custo_puro,
                    "frete": f_item_orc,
                    "embalagem": e_item_orc
                })
                st.rerun()

        # Tabela de Visualização do Orçamento
        if st.session_state.carrinho_orc:
            st.markdown(f"### Itens do Grupo: {grupo_pedido}")
            
            custo_fabrica_total = 0.0
            total_final_venda = 0.0

            # Header
            h = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
            h[0].write("**Produto**")
            h[1].write("**Qtd**")
            h[2].write("**Unit. Puro**")
            h[3].write("**Unit. Final**")
            h[4].write("**Subtotal**")

            for idx, it in enumerate(st.session_state.carrinho_orc):
                c = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
                
                # CÁLCULOS TÉCNICOS INTEGRADOS
                # Custo base = Unitário + Frete + Embalagem
                custo_base = it['custo_unit'] + it['frete'] + it['embalagem']
                
                # Aplicando Quebra (2%) e Despesas (30%) conforme sua base
                custo_producao = custo_base * 1.32 
                
                # Aplicando Margem de Lucro da tela
                valor_venda_unitario = custo_producao * (1 + (margem_lucro / 100))
                
                # Subtotal
                sub_venda = valor_venda_unitario * it['qtd']
                
                custo_fabrica_total += (it['custo_unit'] * it['qtd'])
                total_final_venda += sub_venda

                c[0].write(it['nome'])
                c[1].write(f"x{it['qtd']}")
                c[2].write(f"R$ {it['custo_unit']:.2f}")
                c[3].write(f"R$ {valor_venda_unitario:.2f}")
                c[4].write(f"**R$ {sub_venda:.2f}**")
                
                if c[5].button("❌", key=f"del_{idx}"):
                    st.session_state.carrinho_orc.pop(idx)
                    st.rerun()

            st.divider()
            
            # --- CÁLCULO DE TAXA DE CARTÃO ---
            taxa_fin = total_final_venda * (taxa_credito_input / 100) if forma_pagamento == "Crédito" else 0.0
            total_geral_com_taxa = total_final_venda + taxa_fin

            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.markdown(f"**Total Custo Puro (Sem Lucro):** R$ {custo_fabrica_total:.2f}")
                st.write(f"Margem aplicada: {margem_lucro}%")
                if forma_pagamento == "Crédito":
                    st.write(f"Taxa Cartão ({taxa_credito_input}%): R$ {taxa_fin:.2f}")
            
            with res_col2:
                st.markdown(f"<div style='text-align:right;'><p>VALOR TOTAL DO ORÇAMENTO</p><h2 style='color:#4ade80;'>R$ {total_geral_com_taxa:.2f}</h2></div>", unsafe_allow_html=True)

            # --- BOTÕES DE AÇÃO ---
            st.write("---")
            b1, b2, b3 = st.columns(3)
            
            if b1.button("💾 Salvar Orçamento"):
                df_h = carregar_historico()
                novo = pd.DataFrame([{
                    "Data": data_orc.strftime("%d/%m/%Y"),
                    "Cliente": nome_cliente,
                    "Pedido": grupo_pedido,
                    "Itens": ", ".join([f"{x['nome']} (x{x['qtd']})" for x in st.session_state.carrinho_orc]),
                    "Valor_Final": f"R$ {total_geral_com_taxa:.2f}"
                }])
                conn.update(worksheet="Orcamentos_Salvos", data=pd.concat([df_h, novo], ignore_index=True))
                st.success("Orçamento salvo na planilha!")

            if b2.button("📱 Enviar para WhatsApp"):
                texto_whats = f"*ORÇAMENTO - {nome_cliente}*\n\n"
                texto_whats += f"Grupo: {grupo_pedido}\n"
                for i in st.session_state.carrinho_orc:
                    texto_whats += f"• {i['nome']} x{i['qtd']}\n"
                texto_whats += f"\n*Total Final: R$ {total_geral_com_taxa:.2f}*"
                
                link = f"https://wa.me/{tel_cliente}?text={urllib.parse.quote(texto_whats)}"
                st.markdown(f"[Clique aqui para abrir o WhatsApp]({link})")

            if b3.button("🗑️ Limpar Pedido"):
                st.session_state.carrinho_orc = []
                st.rerun()

    with tab_salvos:
        st.subheader("📋 Histórico de Orçamentos Gravados")
        df_historico = carregar_historico()
        if not df_historico.empty:
            st.dataframe(df_historico, use_container_width=True)
            if st.button("Limpar Histórico Completo"):
                # Limpa a planilha (Cuidado: ação irreversível)
                conn.update(worksheet="Orcamentos_Salvos", data=pd.DataFrame(columns=df_historico.columns))
                st.rerun()
        else:
            st.info("Nenhum orçamento salvo encontrado.")

if __name__ == "__main__":
    main()
