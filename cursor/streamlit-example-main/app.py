"""
大型車休息調査（荷主・元請 / 実運送事業者）ローデータの可視化。
input フォルダ内の CSV を自動検出して読み込みます。
"""

from __future__ import annotations

from pathlib import Path

import japanize_matplotlib  # noqa: F401
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# 都道府県コード F3（GT表「F3	都道府県」に準拠）
PREFECTURE_NAMES: dict[int, str] = {
    1: "北海道",
    2: "青森県",
    3: "岩手県",
    4: "宮城県",
    5: "秋田県",
    6: "山形県",
    7: "福島県",
    8: "茨城県",
    9: "栃木県",
    10: "群馬県",
    11: "埼玉県",
    12: "千葉県",
    13: "東京都",
    14: "神奈川県",
    15: "新潟県",
    16: "富山県",
    17: "石川県",
    18: "福井県",
    19: "山梨県",
    20: "長野県",
    21: "岐阜県",
    22: "静岡県",
    23: "愛知県",
    24: "三重県",
    25: "滋賀県",
    26: "京都府",
    27: "大阪府",
    28: "兵庫県",
    29: "奈良県",
    30: "和歌山県",
    31: "鳥取県",
    32: "島根県",
    33: "岡山県",
    34: "広島県",
    35: "山口県",
    36: "徳島県",
    37: "香川県",
    38: "愛媛県",
    39: "高知県",
    40: "福岡県",
    41: "佐賀県",
    42: "長崎県",
    43: "熊本県",
    44: "大分県",
    45: "宮崎県",
    46: "鹿児島県",
    47: "沖縄県",
}

CAPITAL_NAMES: dict[int, str] = {
    1: "1千万円以下",
    2: "1千万円超～5千万円以下",
    3: "5千万円超～1億円以下",
    4: "1億円超～3億円以下",
    5: "3億円超",
}

# 先頭付近の主な設問（単一回答）— 設問文は調査票・GT表を参照
SHIPPER_CHARTS: list[tuple[str, str]] = [
    ("q1", "Q1 ゆとりのある運送・発注"),
    ("q3", "Q3 休憩・宿泊料の支払い"),
    ("q4", "Q4 改善基準告示の知識"),
    ("q5", "Q5 高速深夜割引見直しの認知"),
    ("q8", "Q8 休息場所の変更予定"),
]

OPERATOR_CHARTS: list[tuple[str, str]] = [
    ("q5", "Q5"),
    ("q7", "Q7"),
    ("q9", "Q9"),
    ("q11_1", "Q11_1"),
    ("q10-1", "Q10-1"),
]


def _input_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "input"


def _find_csv(keyword: str) -> Path:
    base = _input_dir()
    hits = sorted(base.glob(f"*{keyword}*.csv"))
    if not hits:
        raise FileNotFoundError(f"input 内に keyword={keyword!r} に一致する CSV がありません: {base}")
    return hits[0]


@st.cache_data
def load_shipper() -> pd.DataFrame:
    path = _find_csv("荷主")
    return pd.read_csv(path)


@st.cache_data
def load_operator() -> pd.DataFrame:
    path = _find_csv("実運送")
    return pd.read_csv(path)


def _with_pref_cap_labels(
    df: pd.DataFrame, pref_col: str, cap_col: str = "f1"
) -> pd.DataFrame:
    out = df.copy()
    p = pd.to_numeric(out[pref_col], errors="coerce")
    c = pd.to_numeric(out[cap_col], errors="coerce")
    out["_pref_code"] = p
    out["_cap_code"] = c
    out["都道府県"] = p.map(PREFECTURE_NAMES).fillna("（不明・欠損）")
    out["資本金区分"] = c.map(CAPITAL_NAMES).fillna("（不明・欠損）")
    return out


def _filter_df(df: pd.DataFrame, prefs: list[str], caps: list[str]) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if prefs:
        m &= df["都道府県"].isin(prefs)
    if caps:
        m &= df["資本金区分"].isin(caps)
    return df.loc[m]


def _plot_question_series(series: pd.Series, title: str) -> plt.Figure:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "表示できる回答がありません", ha="center", va="center")
        ax.axis("off")
        fig.suptitle(title)
        return fig
    s = s.astype(float)
    s = s[(s >= 0) & (s < 100)].astype(int)
    vc = s.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar([str(i) for i in vc.index], vc.values, color="steelblue")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("回答コード")
    ax.set_ylabel("件数")
    fig.tight_layout()
    return fig


def main() -> None:
    st.set_page_config(page_title="大型車休息調査 可視化", layout="wide")
    st.title("大型車休息調査アンケート（先頭付近の設問）")
    st.caption("データ: リポジトリの `input` フォルダ内 CSV（荷主・元請 / 実運送事業者）")

    try:
        df_ship_raw = load_shipper()
        df_op_raw = load_operator()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    # 荷主・元請: 都道府県=f3 ／ 実運送: 都道府県=f5（コードは同一の県マスタ）
    df_ship = _with_pref_cap_labels(df_ship_raw, pref_col="f3", cap_col="f1")
    df_op = _with_pref_cap_labels(df_op_raw, pref_col="f5", cap_col="f1")

    all_prefs = sorted(
        set(df_ship["都道府県"]) | set(df_op["都道府県"]),
        key=lambda x: (x == "（不明・欠損）", x),
    )
    all_caps = sorted(
        set(df_ship["資本金区分"]) | set(df_op["資本金区分"]),
        key=lambda x: (x == "（不明・欠損）", x),
    )

    with st.sidebar:
        st.header("フィルタ")
        sel_pref = st.multiselect(
            "都道府県",
            options=all_prefs,
            default=[p for p in all_prefs if p != "（不明・欠損）"],
        )
        sel_cap = st.multiselect(
            "資本金",
            options=all_caps,
            default=[c for c in all_caps if c != "（不明・欠損）"],
        )
        st.markdown("---")
        st.markdown(
            "設問の選択肢ラベルは GT表（`input` 内 TSV）を参照してください。"
        )

    tab_ship, tab_op = st.tabs(["荷主・元請け", "実運送事業者"])

    with tab_ship:
        fs = _filter_df(df_ship, sel_pref, sel_cap)
        st.write(f"対象件数: **{len(fs)}** 件（荷主・元請）")
        if fs.empty:
            st.warning("条件に合うデータがありません。フィルタを緩めてください。")
        else:
            cols = st.columns(2)
            for i, (col, ttl) in enumerate(SHIPPER_CHARTS):
                if col not in fs.columns:
                    continue
                fig = _plot_question_series(fs[col], ttl)
                cols[i % 2].pyplot(fig)
                plt.close(fig)

    with tab_op:
        fo = _filter_df(df_op, sel_pref, sel_cap)
        st.write(f"対象件数: **{len(fo)}** 件（実運送事業者）")
        if fo.empty:
            st.warning("条件に合うデータがありません。フィルタを緩めてください。")
        else:
            cols = st.columns(2)
            for i, (col, ttl) in enumerate(OPERATOR_CHARTS):
                if col not in fo.columns:
                    continue
                fig = _plot_question_series(fo[col], ttl)
                cols[i % 2].pyplot(fig)
                plt.close(fig)


if __name__ == "__main__":
    main()

# test, this line does nothing