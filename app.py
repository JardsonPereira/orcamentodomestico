import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais. Verifique os Secrets.")
    st.stop()

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    # --- CONFIGURAÇÃO VISUAL ---
    st.set_page_config(page_title="ContabilApp Pro", layout="wide", page_icon="💰")
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #F0F2F5; }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3.2em;
            font-weight: 600;
            transition: all 0.2s;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.logado:
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        
        with col_central:
            escolha = st.radio("Selecione uma opção:", ["Entrar na Conta", "Criar Nova Conta"], horizontal=True, label_visibility="collapsed")
            
            with st.container(border=True):
                if escolha == "Entrar na Conta":
                    st.subheader("Bem-vindo de volta")
                    email = st.text_input("E-mail", placeholder="seu@email.com")
                    senha = st.text_input("Senha", type='password', placeholder="••••••••")
                    nome_fantasia = st.text_input("Como quer ser chamado?", placeholder="Ex: João")
                    
                    if st.button("ACESSAR SISTEMA"):
                        try:
                            supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            st.session_state.logado = True
                            st.session_state.user_email = email
                            st.session_state.user_name = nome_fantasia
                            st.rerun()
                        except:
                            st.error("E-mail ou senha incorretos.")
                            
                else:
                    st.subheader("Comece agora mesmo")
                    novo_nome = st.text_input("Seu Nome", placeholder="Ex: Maria")
                    novo_email = st.text_input("E-mail", placeholder="exemplo@email.com")
                    nova_senha = st.text_input("Crie uma senha", type='password', placeholder="mínimo 6 caracteres")
                    
                    if st.button("CRIAR MINHA CONTA"):
                        try:
                            # Tenta cadastrar o usuário
                            res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                            
                            # Se o e-mail confirm estiver desativado no Supabase, logamos direto
                            st.session_state.logado = True
                            st.session_state.user_email = novo_email
                            st.session_state.user_name = novo_nome
                            st.success("Conta criada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao cadastrar: {e}")

    else:
        # --- SISTEMA APÓS LOGIN ---
        col_title, col_user = st.columns([3, 1])
        with col_title:
            nome = st.session_state.get('user_name', 'Usuário')
            st.title(f"💰 Olá, {nome}")
            
        with col_user:
            with st.expander(f"👤 Perfil"):
                st.write(f"ID: {st.session_state.user_email}")
                if st.button("Encerrar Sessão"):
                    st.session_state.logado = False
                    st.session_state.user_name = ""
                    st.rerun()

        # --- BUSCA DE DADOS ---
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs([
            "➕ Lançar", "📊 Extrato", "💳 Cartões", "⚙️ Editar", "🛠️ Ajustes"
        ])

        with tab_lanc:
            st.subheader("Registrar Movimentação")
            metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"], key="metodo_pag")
            
            cart_vontade = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes:
                    cart_vontade = st.selectbox("Selecione o Cartão", lista_cartoes, key="card_ativo")
                else:
                    st.warning("Cadastre um cartão primeiro.")

            with st.form("form_mobile", clear_on_submit=True):
                col1, col2 = st.columns(2)
                tipo = col1.selectbox("Tipo", ["Despesa", "Receita"])
                desc = col2.text_input("Descrição")
                
                col3, col4 = st.columns(2)
                valor_total = col3.number_input("Valor Total (R$)", min_value=0.01, step=0.10)
                data_origem = col4.date_input("Data", datetime.now())
                
                total_parc = 1
                if metodo_sel == "Cartão de Crédito":
                    total_parc = st.number_input("Número de Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 SALVAR LANÇAMENTO"):
                    u_email = st.session_state.get('user_email')
                    v_parc = valor_total / int(total_parc)
                    for i in range(int(total_parc)):
                        data_venc = add_months(data_origem, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parc, 2), "date": data_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_sel, "card_name": cart_vontade,
                            "installment_total": int(total_parc), "installment_number": i + 1
                        }).execute()
                    st.success("✅ Lançado!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses_disponiveis = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                mes_atual_str = datetime.now().strftime('%m/%Y')
                try: default_idx = meses_disponiveis.index(mes_atual_str)
                except: default_idx = len(meses_disponiveis) - 1

                mes_sel = st.radio("Filtrar Período:", meses_disponiveis, index=default_idx, horizontal=True)
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                
                m1, m2, m3 = st.columns(3)
                rec_total = f[f['type'] == 'Receita']['amount'].sum()
                des_total = f[f['type'] == 'Despesa']['amount'].sum()
                m1.metric("Receitas", f"R$ {rec_total:,.2f}")
                m2.metric("Despesas", f"R$ {des_total:,.2f}")
                m3.metric("Saldo", f"R$ {rec_total-des_total:,.2f}")

                st.markdown("---")
                col_rec, col_des = st.columns(2)
                
                with col_rec:
                    st.markdown("### 🟢 Entradas")
                    df_rec = f[f['type'] == 'Receita'][['date', 'category', 'amount']].copy()
                    if not df_rec.empty:
                        df_rec['date'] = df_rec['date'].dt.strftime('%d/%m')
                        st.dataframe(df_rec, use_container_width=True, hide_index=True)
                
                with col_des:
                    st.markdown("### 🔴 Saídas")
                    df_des = f[f['type'] == 'Despesa'][['date', 'category', 'amount']].copy()
                    if not df_des.empty:
                        df_des['date'] = df_des['date'].dt.strftime('%d/%m')
                        st.dataframe(df_des, use_container_width=True, hide_index=True)
            else: st.info("Nenhum dado encontrado.")

        with tab_cartao:
            if not df.empty and lista_cartoes:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                df_c['date'] = pd.to_datetime(df_c['date'])
                hoje = datetime.now()
                
                for nome_cartao in lista_cartoes:
                    with st.container(border=True):
                        st.subheader(f"💳 {nome_cartao}")
                        dados_este_cartao = df_c[df_c['card_name'] == nome_cartao]
                        if not dados_este_cartao.empty:
                            total_fatura = dados_este_cartao[dados_este_cartao['date'].dt.strftime('%m/%Y') == hoje.strftime('%m/%Y')]['amount'].sum()
                            st.metric("Fatura do Mês", f"R$ {total_fatura:,.2f}")
                            
                            resumo = []
                            for (desc, total), grupo in dados_este_cartao.groupby(['category', 'installment_total']):
                                grupo = grupo.sort_values('date')
                                proximas = grupo[grupo['date'] >= hoje.replace(day=1)]
                                if not proximas.empty:
                                    resumo.append({
                                        'Venc.': proximas.iloc[0]['date'].strftime('%d/%m'),
                                        'Item': desc,
                                        'Parc.': f"{int(proximas.iloc[0]['installment_number'])}/{int(total)}",
                                        'Valor': f"R$ {proximas.iloc[0]['amount']:,.2f}"
                                    })
                            st.table(pd.DataFrame(resumo))
            else: st.info("Cadastre cartões nos ajustes.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                df_edit['card_name'] = df_edit['card_name'].fillna('N/A')
                
                df_grouped = df_edit.sort_values(['category', 'card_name', 'installment_total', 'date'])
                df_grouped = df_grouped.groupby(['category', 'card_name', 'installment_total', 'payment_method', 'type'], as_index=False, dropna=False).first()
                df_grouped = df_grouped.sort_values(by='date', ascending=False)
                
                opcoes = {}
                for _, r in df_grouped.iterrows():
                    v_total = float(r['amount']) * int(r['installment_total'])
                    prefixo = "💰" if r['type'] == 'Receita' else "💸"
                    label = f"{prefixo} {r['date'].strftime('%d/%m/%y')} | {r['category']} - R${v_total:,.2f}"
                    opcoes[label] = r['id']
                
                item_sel = st.selectbox("Selecione o registro para editar", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                d_at = df[df['id'] == id_alvo].iloc[0]

                with st.form("edit_form"):
                    n_desc = st.text_input("Alterar Descrição", value=d_at['category'])
                    n_valor_full = st.number_input("Alterar Valor Total", value=float(d_at['amount']) * int(d_at['installment_total']))
                    n_data_base = st.date_input("Alterar Data", pd.to_datetime(d_at['date']))
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 ATUALIZAR"):
                        relacionadas = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total']) & (df['type'] == d_at['type'])]
                        v_nova_parc = n_valor_full / int(d_at['installment_total'])
                        for idx, row in relacionadas.iterrows():
                            nova_data = add_months(n_data_base, int(row['installment_number']) - 1)
                            supabase.table("profile_transactions").update({"category": n_desc, "amount": round(v_nova_parc, 2), "date": nova_data.strftime("%Y-%m-%d")}).eq("id", row['id']).execute()
                        st.success("Atualizado!")
                        st.rerun()
                        
                    if c2.form_submit_button("🗑️ EXCLUIR"):
                        relacionadas = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total']) & (df['type'] == d_at['type'])]
                        for _, row in relacionadas.iterrows():
                            supabase.table("profile_transactions").delete().eq("id", row['id']).execute()
                        st.rerun()

        with tab_config:
            st.subheader("Ajustes")
            col_a, col_b = st.columns(2)
            with col_a:
                n_c = st.text_input("Nome do Novo Cartão")
                if st.button("Adicionar Cartão"):
                    if n_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                        st.rerun()
            with col_b:
                if lista_cartoes:
                    cart_del = st.selectbox("Remover Cartão", lista_cartoes)
                    if st.button("Excluir Cartão"):
                        supabase.table("my_cards").delete().eq("id", dict_cartoes[cart_del]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
