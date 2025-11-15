import streamlit as st
import pandas as pd
import plotly
import plotly.express as px

def clean_price(price):
    """Fungsi untuk membersihkan data harga (menghapus ',' dan mengubah ke angka)"""
    if isinstance(price, str):
        # Hapus koma dan spasi
        price = price.replace(',', '').strip()
        # Jika ada data '-' (kosong), anggap sebagai 0 atau NaN
        if price == '-' or price == '':
            return pd.NA
    try:
        return int(price)
    except (ValueError, TypeError):
        return pd.NA

def load_data(uploaded_file):
    """Fungsi untuk memuat dan mentransformasi data dari file yang di-upload."""
    
    if uploaded_file is None:
        st.error("Silakan upload file 'Tabel Harga Berdasarkan Komoditas.xlsx' di sidebar.")
        return None

    try:
        # Coba baca sebagai Excel terlebih dahulu
        df_wide = pd.read_excel(uploaded_file)
    except Exception as e_excel:
        try:
            # Jika gagal, coba baca sebagai CSV
            # Pindahkan pointer file kembali ke awal
            uploaded_file.seek(0)
            df_wide = pd.read_csv(uploaded_file)
        except Exception as e_csv:
            st.error(f"Gagal membaca file. Pastikan formatnya Excel atau CSV. Error: {e_csv}")
            return None

    # --- Pembersihan Awal ---
    # Ganti nama kolom 'Komoditas (Rp)' menjadi 'Provinsi' agar lebih mudah
    if 'Komoditas (Rp)' in df_wide.columns:
         df_wide = df_wide.rename(columns={'Komoditas (Rp)': 'Provinsi'})
    else:
        st.error("Data tidak memiliki kolom 'Komoditas (Rp)'. Pastikan file Anda benar.")
        return None

    # Hapus kolom yang tidak perlu jika ada (misal kolom 'No')
    if 'No' in df_wide.columns:
        df_wide = df_wide.drop(columns=['No'])
        
    # Hapus baris yang provinsinya kosong (jika ada, misal baris total)
    df_wide = df_wide.dropna(subset=['Provinsi'])

    # Set 'Provinsi' sebagai index untuk pembersihan
    df_wide = df_wide.set_index('Provinsi')

    # Bersihkan semua kolom tanggal
    for col in df_wide.columns:
        df_wide[col] = df_wide[col].apply(clean_price)
    
    df_wide.columns = df_wide.columns.astype(str).str.strip()
    # Hapus baris yang semua datanya kosong (jika ada)
    df_wide = df_wide.dropna(how='all')

    # --- Transformasi Data (Penting) ---
    # Mengubah data dari format 'wide' (lebar) ke 'long' (panjang)
    df_long = df_wide.reset_index().melt(
        id_vars='Provinsi', 
        var_name='Tanggal', 
        value_name='Harga'
    )
    
    df_long['Tanggal'] = df_long['Tanggal'].str.replace(' ', '')

    # Konversi kolom 'Tanggal' ke format datetime
    try:
        # Coba format DD/MM/YYYY terlebih dahulu (dari gambar)
       df_long['Tanggal'] = pd.to_datetime(df_long['Tanggal'], format='%d/%m/%Y')
    except ValueError:
        try:
            # Jika gagal, coba format lain (misal YYYY-MM-DD jika file Excel berbeda)
            df_long['Tanggal'] = pd.to_datetime(df_long['Tanggal'])
        except Exception as e_date:
            st.error(f"Format tanggal di header kolom salah. Error: {e_date}")
            return None

    # Hapus data yang harganya kosong (NA) setelah di-melt
    df_long = df_long.dropna(subset=['Harga'])
    
    # Ubah harga ke integer
    df_long['Harga'] = df_long['Harga'].astype(int)
    
    # Urutkan data berdasarkan tanggal
    df_long = df_long.sort_values(by='Tanggal')
    
    # kembalikan df_long (untuk plot) dan df_wide (untuk statistik deskriptif)
    return df_long, df_wide.transpose() 

# --- Konfigurasi Halaman Utama GUI ---
st.set_page_config(layout="wide")
st.title('Dashboard Analisis Harga Beras 2024 🍚')

# --- Sidebar untuk Kontrol ---
st.sidebar.header('Kontrol Data')

# Opsi upload file
uploaded_file = st.sidebar.file_uploader(
    "Upload file Excel/CSV Harga Beras Anda", 
    type=["csv", "xlsx"]
)

# Memuat data
if uploaded_file is not None:
    data_load_state = st.info("Memproses file data...")
    data = load_data(uploaded_file)
    
    if data:
        df_long, df_stats_ready = data
        data_load_state.success("Data berhasil diproses!")

        # Ambil daftar provinsi dan tanggal unik
        provinsi_list = sorted(df_long['Provinsi'].unique())
        # Ambil tanggal unik dan format kembali ke string
        tanggal_list_str = df_long['Tanggal'].dt.strftime('%d/%m/%Y').unique()

        # --- Kontrol Pilihan di Sidebar ---
        st.sidebar.subheader("Filter Diagram Garis")
        selected_provinsi = st.sidebar.multiselect(
            'Pilih Provinsi (bisa lebih dari satu):',
            options=provinsi_list,
            default=list(provinsi_list[:2]) # Ambil 2 provinsi pertama sebagai default
        )

        st.sidebar.subheader("Filter Diagram Batang")
        selected_tanggal = st.sidebar.selectbox(
            'Pilih Tanggal Tunggal:',
            options=tanggal_list_str,
            index=len(tanggal_list_str) - 1 # Default tanggal terakhir
        )

        # --- Area Utama: Visualisasi ---

        ## 1. Diagram Garis (Analisis Tren)
        st.header('📈 Diagram Garis: Tren Harga Beras per Provinsi')
        if not selected_provinsi:
            st.warning('Silakan pilih minimal satu provinsi di sidebar untuk menampilkan diagram garis.')
        else:
            # Filter data berdasarkan provinsi yang dipilih
            df_garis = df_long[df_long['Provinsi'].isin(selected_provinsi)]
            
            # Buat diagram garis dengan Plotly
            fig_garis = px.line(
                df_garis,
                x='Tanggal',
                y='Harga',
                color='Provinsi',
                title='Tren Harga Beras Harian',
                markers=True,
                labels={'Harga': 'Harga (Rp)', 'Provinsi': 'Lokasi'}
            )
            st.plotly_chart(fig_garis, use_container_width=True)

        ## 2. Diagram Batang (Analisis Perbandingan)
        st.header('📊 Diagram Batang: Perbandingan Harga per Tanggal')
        
        # Filter data berdasarkan tanggal yang dipilih
        df_batang = df_long[df_long['Tanggal'] == pd.to_datetime(selected_tanggal, format='%d/%m/%Y')]
        
        # Urutkan data untuk tampilan bar chart yang lebih baik
        df_batang = df_batang.sort_values(by='Harga', ascending=False)
        
        # Buat diagram batang dengan Plotly
        fig_batang = px.bar(
            df_batang,
            x='Provinsi',
            y='Harga',
            color='Harga',
            color_continuous_scale='Reds',
            title=f'Perbandingan Harga Beras pada {selected_tanggal}',
            labels={'Harga': 'Harga (Rp)', 'Provinsi': 'Lokasi'}
        )
        st.plotly_chart(fig_batang, use_container_width=True)

        # --- 3. Analisis Statistika Sederhana ---
        st.header('🔬 Analisis Statistika Sederhana')
        
        st.subheader('Statistik Deskriptif (Ringkasan 5 Angka)')
        st.info("Ringkasan statistik (mean, std, min, max, kuartil) untuk setiap provinsi selama periode data.")
        # Kita gunakan data yang sudah ditranspose dan dibersihkan
        st.dataframe(df_stats_ready.describe().round(2))

        st.subheader('Detail untuk Provinsi Terpilih')
        if selected_provinsi:
            df_stats_filtered = df_long[df_long['Provinsi'].isin(selected_provinsi)]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Harga Rata-rata (Terpilih)", f"Rp {df_stats_filtered['Harga'].mean():,.0f}")
            col2.metric("Harga Tertinggi (Terpilih)", f"Rp {df_stats_filtered['Harga'].max():,.0f}")
            col3.metric("Harga Terendah (Terpilih)", f"Rp {df_stats_filtered['Harga'].min():,.0f}")
            
            st.markdown("**Data Rata-rata per Provinsi (Terpilih):**")
            df_avg = df_stats_filtered.groupby('Provinsi')['Harga'].mean().reset_index()
            df_avg['Harga'] = df_avg['Harga'].round(0)
            st.dataframe(df_avg.sort_values(by='Harga', ascending=False), use_container_width=True)
        else:
            st.info("Pilih provinsi di sidebar untuk melihat statistik detail.")

else:
    st.info("Silakan upload file Excel atau CSV Anda untuk memulai analisis.")