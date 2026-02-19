import streamlit as st
import pandas as pd
import os
import re
import io
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. 画面設定 ---
st.set_page_config(
    layout="wide", 
    page_title="DITS 統合検索システム",
    # 検索エンジンにインデックスされにくくするための設定
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# --- 2. セキュリティ・認証設定 ---
# STAFF IDを追加しました
USER_DB = {
    "minobe": "Genuemon320",
    "ikeda": "$Dits0401",
    "shudo": "$Dits0401",
    "dits": "$Dits0401"

}

def check_password():
    if "authenticated" not in st.session_state:
        st.title("🔐 DITS System Login")
        user = st.text_input("User ID")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            if user in USER_DB and USER_DB[user] == pw:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.rerun()
            else: st.error("IDまたはパスワードが違います")
        return False
    return True

# --- 3. ログ記録関数 ---
def write_log(action, detail=""):
    log_file = "usage_log.csv"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = st.session_state.get("user", "unknown")
    new_log = pd.DataFrame([[now, user, action, detail]], columns=["Datetime", "User", "Action", "Detail"])
    if os.path.exists(log_file):
        new_log.to_csv(log_file, mode='a', header=False, index=False, encoding='utf_8_sig')
    else:
        new_log.to_csv(log_file, mode='w', header=True, index=False, encoding='utf_8_sig')

# --- 4. メインアプリケーション ---
if check_password():
    try:
        # CSS注入（中央寄せ）
        st.markdown("<style>.stTable td, .stTable th { text-align: center !important; } [data-testid='stTable'] { text-align: center; }</style>", unsafe_allow_html=True)

        # リンクマップ
        SUPPLIER_LINKS = {
            "MOUSER": "https://www.mouser.jp/", "DIGIKEY": "https://www.digikey.jp/",
            "DIGIKY": "https://www.digikey.jp/", "CHIP1": "https://www.chip1stop.com/",
            "CHIP": "https://www.chip1stop.com/", "コアスタッフ": "https://www.zaikostore.com/zaikostore/",
            "RS": "https://jp.rs-online.com/web/", "YAHOO": "https://shopping.yahoo.co.jp/",
            "AMAZON": "https://www.amazon.co.jp/", "APPLE": "https://www.apple.com/jp-edu/store",
            "楽天": "https://www.rakuten.co.jp/", "モノタロウ": "https://www.monotaro.com/",
            "アスクル": "https://www.askul.co.jp/", "ビックカメラ": "https://www.biccamera.com/bc/main/",
            "ヨドバシ": "https://www.yodobashi.com/", "ミスミ": "https://jp.misumi-ec.com/"
        }

        def copy_button_right_html(text):
            html_code = f"""
            <div style="text-align: right; width: 100%; padding-bottom: 5px;">
                <button onclick="copyToClipboard('{text}')" style="
                    background-color: #ffffff; border: 1px solid #ff4b4b; border-radius: 20px;
                    padding: 4px 15px; cursor: pointer; font-size: 13px; font-weight: bold; color: #ff4b4b;
                "> 📋 {text} をコピー </button>
            </div>
            <script>
            function copyToClipboard(text) {{
                const el = document.createElement('textarea');
                el.value = text; document.body.appendChild(el);
                el.select(); document.execCommand('copy'); document.body.removeChild(el);
            }}
            </script>
            """
            return components.html(html_code, height=40)

        def format_currency(val):
            try:
                s = str(val).replace(',', '').replace('¥', '').replace(' ', '').lower()
                if not s or s in ["nan", "none", "", "-", "0", "0.0"]: return ""
                return f"¥{float(s):,.0f}"
            except: return ""

        def convert_to_magic_link(name):
            if not name: return ""
            un = str(name).strip().upper()
            for k, u in SUPPLIER_LINKS.items():
                if k in un: return f"{u}#{name}"
            return name

        @st.cache_data(show_spinner=False)
        def load_data():
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, "summary_data.xls")
            if not os.path.exists(file_path):
                file_path = os.path.join(base_dir, "summary_data.xlsx")
            
            engine = 'xlrd' if file_path.endswith('.xls') else 'openpyxl'
            xls = pd.ExcelFile(file_path, engine=engine)
            
            combined = []
            target_cols = ['参照月', '客先納期', '注番', '型番', '備考', '販売先', '納入先', '担当者', '数量', '仕入値', '仕入値合価', '売値', '売値合価', '仕入先']
            alias_map = {'納入日': '客先納期', '型式': '型番', '品名': '型番', '依頼者': '担当者', '担当': '担当者', 'メーカ': '仕入先'}
            ignore = ['ピボット１', 'ピボット２', '注番シート', 'ラベル', 'Sheet2', '検査票', '統合データ', 'summary_data']
            
            for sn in [s for s in xls.sheet_names if s not in ignore]:
                try:
                    df = pd.read_excel(xls, sheet_name=sn, header=None)
                    h_idx = -1
                    for r in range(min(25, len(df))):
                        row_vals = [str(v).strip() for v in df.iloc[r].values]
                        if any(k in row_vals for k in ['型番', '型式', '品名', '注番']):
                            h_idx = r; break
                    if h_idx == -1: continue 
                    tdf = df.iloc[h_idx+1:].copy()
                    tdf.columns = [alias_map.get(str(c).strip(), str(c).strip()) for c in df.iloc[h_idx]]
                    tdf = tdf.loc[:, ~tdf.columns.duplicated()]
                    tdf['参照月'] = sn
                    combined.append(tdf.reindex(columns=target_cols, fill_value=""))
                except: continue
            
            df_m = pd.concat(combined, ignore_index=True)
            for col in df_m.columns:
                if col == '客先納期':
                    df_m[col] = pd.to_datetime(df_m[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")
                else:
                    df_m[col] = df_m[col].apply(lambda x: str(x).strip().replace(".0", "") if pd.notnull(x) and str(x).strip().lower() not in ["nan", "none", "0", "0.0", "00:00:00"] else "")
            
            df_m = df_m[df_m['型番'] != ""]
            
            def d_info(s):
                res = re.findall(r'(\d+)', str(s))
                if len(res) >= 2:
                    y, m = int(res[0])+2000, int(res[1])
                    return y, m, y*100 + m
                return 0, 0, 0
            
            df_m[['年度', '月', 'sort_key']] = df_m['参照月'].apply(lambda x: pd.Series(d_info(x)))
            return df_m.sort_values('sort_key', ascending=False).drop(columns=['sort_key']).astype(str)

        df_master = load_data()
        
        st.sidebar.title(f"👤 {st.session_state.user}")
        if st.sidebar.button("Logout"):
            del st.session_state.authenticated
            st.rerun()

        st.sidebar.header("🔍 検索メニュー")
        # ラベルを変更
        q = st.sidebar.text_input("［ 型番 or 注番 ］ 検索").strip().upper()
        f = st.sidebar.file_uploader("CSVで一斉検索", type=["csv"])
        
        keywords = []
        if q: keywords.append(q)
        if f:
            content = f.read()
            for enc in ['utf-8-sig', 'cp932']:
                try:
                    b_df = pd.read_csv(io.BytesIO(content), encoding=enc, header=None)
                    keywords.extend(b_df[0].dropna().astype(str).str.strip().str.upper().tolist())
                    break
                except: continue

        if keywords:
            for kw in list(dict.fromkeys([k for k in keywords if k != "型番リスト"])):
                # 型番と注番の両方を検索対象に修正
                res = df_master[
                    (df_master['型番'].str.upper().str.contains(re.escape(kw), na=False)) | 
                    (df_master['注番'].str.upper().str.contains(re.escape(kw), na=False))
                ].copy()
                
                if not res.empty:
                    write_log("Search", kw)
                    st.markdown("---")
                    c_t, c_c = st.columns([0.6, 0.4])
                    with c_t: st.subheader(kw)
                    with c_c: copy_button_right_html(kw)
                    ddf = res.copy()
                    for c in ['仕入値', '仕入値合価', '売値', '売値合価']: ddf[c] = ddf[c].apply(format_currency)
                    ddf['仕入先'] = ddf['仕入先'].apply(convert_to_magic_link)
                    st.dataframe(ddf.drop(columns=['年度', '月']).head(3), use_container_width=True, 
                                 column_config={"仕入先": st.column_config.LinkColumn("仕入先", display_text=r"#(.*)")})
                    if len(ddf) > 3:
                        with st.expander("▶︎ 過去分"):
                            st.dataframe(ddf.drop(columns=['年度', '月']).iloc[3:], use_container_width=True, 
                                         column_config={"仕入先": st.column_config.LinkColumn("仕入先", display_text=r"#(.*)")})
                else: st.sidebar.warning(f"「{kw}」実績なし")
        else:
            st.info("左のサイドバーから検索してください。")
            summary = df_master.groupby(['年度', '月']).size().reset_index(name='count')
            summary['年度_int'] = summary['年度'].apply(lambda x: int(float(x)))
            summary['月_int'] = summary['月'].apply(lambda x: int(float(x)))
            view = summary.pivot(index='年度_int', columns='月_int', values='count').reindex(columns=range(1,13))
            view.columns = [f"{m}月" for m in view.columns]
            view.index = [f"{i}年" for i in view.index]
            st.write("### 📊 年度別・月別 データ登録件数一覧")
            st.table(view.sort_index(ascending=False).applymap(lambda x: f"{int(x):,}" if pd.notnull(x) else ""))
            
            st.markdown("---")
            st.write("### 📂 月別全件表示")
            c1, c2, _ = st.columns([0.2, 0.2, 0.6])
            yl = sorted(df_master['年度'].unique(), key=lambda x: int(float(x)), reverse=True)
            sy = c1.selectbox("年度を選択", yl)
            am = sorted(df_master[df_master['年度'] == sy]['月'].unique(), key=lambda x: int(float(x)))
            sm = c2.selectbox("月を選択", am)
            if sy and sm:
                write_log("ViewMonthly", f"{sy}-{sm}")
                mdf = df_master[(df_master['年度'] == sy) & (df_master['月'] == sm)].copy()
                for c in ['仕入値', '仕入値合価', '売値', '売値合価']: mdf[c] = mdf[c].apply(format_currency)
                mdf['仕入先'] = mdf['仕入先'].apply(convert_to_magic_link)
                st.dataframe(mdf.drop(columns=['年度', '月']), use_container_width=True, 
                             column_config={"仕入先": st.column_config.LinkColumn("仕入先", display_text=r"#(.*)")})

        if st.session_state.get("user") == "Minobe":
            st.sidebar.markdown("---")
            if os.path.exists("usage_log.csv"):
                with open("usage_log.csv", "rb") as fl:
                    st.sidebar.download_button("📥 ログ(CSV)を保存", fl, "usage_log.csv", "text/csv")
        st.sidebar.metric("総登録件数", f"{len(df_master):,} 件")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")