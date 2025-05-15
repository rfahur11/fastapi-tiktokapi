import numpy as np
import pandas as pd
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from sklearn.preprocessing import MinMaxScaler
from typing import Dict, List, Any, Tuple

class FuzzyRanking:
    def __init__(self):
        # Definisikan Fuzzy System dengan Data Normalisasi
        # Semua variabel input berada dalam rentang [0,1]
        self.cost_norm = ctrl.Antecedent(np.arange(0, 1.001, 0.001), 'cost_norm')
        self.clicks_norm = ctrl.Antecedent(np.arange(0, 1.001, 0.001), 'clicks_norm')
        self.impressions_norm = ctrl.Antecedent(np.arange(0, 1.001, 0.001), 'impressions_norm')
        
        # Output ranking juga pada skala 0 sampai 1
        self.ranking = ctrl.Consequent(np.arange(0, 1.001, 0.001), 'ranking')
        
        # Setup membership functions
        self._setup_membership_functions()
        
        # Setup rules
        self._setup_rules()
        
        # Buat sistem kontrol
        self.ranking_ctrl = ctrl.ControlSystem(self.rules)
        self.ranking_simulation = ctrl.ControlSystemSimulation(self.ranking_ctrl)
    
    def _setup_membership_functions(self):
        """Mendefinisikan fungsi keanggotaan untuk masing-masing variabel"""
        # Cost membership functions
        self.cost_norm['low'] = fuzz.trimf(self.cost_norm.universe, [0, 0, 0.0543])
        self.cost_norm['medium'] = fuzz.trimf(self.cost_norm.universe, [0.0272, 0.0543, 0.2716])
        self.cost_norm['high'] = fuzz.trimf(self.cost_norm.universe, [0.0543, 1, 1])
        
        # Clicks membership functions
        self.clicks_norm['low'] = fuzz.trimf(self.clicks_norm.universe, [0, 0, 0.0547])
        self.clicks_norm['medium'] = fuzz.trimf(self.clicks_norm.universe, [0.0273, 0.1823, 0.546])
        self.clicks_norm['high'] = fuzz.trimf(self.clicks_norm.universe, [0.1823, 1, 1])
        
        # Impressions membership functions
        self.impressions_norm['low'] = fuzz.trimf(self.impressions_norm.universe, [0, 0, 0.0204])
        self.impressions_norm['medium'] = fuzz.trimf(self.impressions_norm.universe, [0.0204, 0.051, 0.102])
        self.impressions_norm['high'] = fuzz.trimf(self.impressions_norm.universe, [0.051, 1, 1])
        
        # Ranking output membership functions
        self.ranking['low'] = fuzz.trimf(self.ranking.universe, [0, 0, 0.5])
        self.ranking['medium'] = fuzz.trimf(self.ranking.universe, [0.25, 0.5, 0.75])
        self.ranking['high'] = fuzz.trimf(self.ranking.universe, [0.5, 1, 1])
    
    def _setup_rules(self):
        """Membuat aturan fuzzy"""
        # Aturan untuk kombinasi Cost (low), Clicks (low), Impressions (?)
        rule1  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['low']    & self.impressions_norm['low'],    self.ranking['low'])    # score: 1+0+0 = 1
        rule2  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['low']    & self.impressions_norm['medium'], self.ranking['medium']) # score: 1+0+0.5 = 1.5
        rule3  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['low']    & self.impressions_norm['high'],   self.ranking['high'])   # score: 1+0+1 = 2

        # Aturan untuk kombinasi Cost (low), Clicks (medium), Impressions (?)
        rule4  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['medium'] & self.impressions_norm['low'],    self.ranking['medium']) # score: 1+0.5+0 = 1.5
        rule5  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['medium'] & self.impressions_norm['medium'], self.ranking['high'])   # score: 1+0.5+0.5 = 2
        rule6  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['medium'] & self.impressions_norm['high'],   self.ranking['high'])   # score: 1+0.5+1 = 2.5

        # Aturan untuk kombinasi Cost (low), Clicks (high), Impressions (?)
        rule7  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['high']   & self.impressions_norm['low'],    self.ranking['high'])   # score: 1+1+0 = 2
        rule8  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['high']   & self.impressions_norm['medium'], self.ranking['high'])   # score: 1+1+0.5 = 2.5
        rule9  = ctrl.Rule(self.cost_norm['low']    & self.clicks_norm['high']   & self.impressions_norm['high'],   self.ranking['high'])   # score: 1+1+1 = 3

        # Aturan untuk kombinasi Cost (medium), Clicks (low), Impressions (?)
        rule10 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['low']    & self.impressions_norm['low'],    self.ranking['low'])    # score: 0.5+0+0 = 0.5
        rule11 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['low']    & self.impressions_norm['medium'], self.ranking['low'])    # score: 0.5+0+0.5 = 1
        rule12 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['low']    & self.impressions_norm['high'],   self.ranking['medium']) # score: 0.5+0+1 = 1.5

        # Aturan untuk kombinasi Cost (medium), Clicks (medium), Impressions (?)
        rule13 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['medium'] & self.impressions_norm['low'],    self.ranking['low'])    # score: 0.5+0.5+0 = 1
        rule14 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['medium'] & self.impressions_norm['medium'], self.ranking['medium']) # score: 0.5+0.5+0.5 = 1.5
        rule15 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['medium'] & self.impressions_norm['high'],   self.ranking['high'])   # score: 0.5+0.5+1 = 2

        # Aturan untuk kombinasi Cost (medium), Clicks (high), Impressions (?)
        rule16 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['high']   & self.impressions_norm['low'],    self.ranking['medium']) # score: 0.5+1+0 = 1.5
        rule17 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['high']   & self.impressions_norm['medium'], self.ranking['high'])   # score: 0.5+1+0.5 = 2
        rule18 = ctrl.Rule(self.cost_norm['medium'] & self.clicks_norm['high']   & self.impressions_norm['high'],   self.ranking['high'])   # score: 0.5+1+1 = 2.5

        # Aturan untuk kombinasi Cost (high), Clicks (low), Impressions (?)
        rule19 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['low']    & self.impressions_norm['low'],    self.ranking['low'])    # score: 0+0+0 = 0
        rule20 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['low']    & self.impressions_norm['medium'], self.ranking['low'])    # score: 0+0+0.5 = 0.5
        rule21 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['low']    & self.impressions_norm['high'],   self.ranking['low'])    # score: 0+0+1 = 1

        # Aturan untuk kombinasi Cost (high), Clicks (medium), Impressions (?)
        rule22 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['medium'] & self.impressions_norm['low'],    self.ranking['low'])    # score: 0+0.5+0 = 0.5
        rule23 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['medium'] & self.impressions_norm['medium'], self.ranking['low'])    # score: 0+0.5+0.5 = 1
        rule24 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['medium'] & self.impressions_norm['high'],   self.ranking['medium']) # score: 0+0.5+1 = 1.5

        # Aturan untuk kombinasi Cost (high), Clicks (high), Impressions (?)
        rule25 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['high']   & self.impressions_norm['low'],    self.ranking['low'])    # score: 0+1+0 = 1
        rule26 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['high']   & self.impressions_norm['medium'], self.ranking['medium']) # score: 0+1+0.5 = 1.5
        rule27 = ctrl.Rule(self.cost_norm['high']   & self.clicks_norm['high']   & self.impressions_norm['high'],   self.ranking['high'])   # score: 0+1+1 = 2

        # Gabungkan semua aturan
        self.rules = [rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, 
                 rule10, rule11, rule12, rule13, rule14, rule15, rule16, rule17, rule18, 
                 rule19, rule20, rule21, rule22, rule23, rule24, rule25, rule26, rule27]

    def compute_ranking(self, row: Dict[str, float]) -> float:
        """Menghitung ranking berdasarkan input data yang sudah dinormalisasi"""
        self.ranking_simulation.reset()  # Reset simulasi untuk setiap perhitungan

        try:
            self.ranking_simulation.input['cost_norm'] = row['cost_norm']
            self.ranking_simulation.input['clicks_norm'] = row['clicks_norm']
            self.ranking_simulation.input['impressions_norm'] = row['impressions_norm']
            
            self.ranking_simulation.compute()
            
            result = self.ranking_simulation.output.get('ranking', 0)
            return result
        except Exception as e:
            print(f"Error computing ranking: {e}")
            return 0

    def normalize_data(self, data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, MinMaxScaler]]:
        """Normalisasi data menggunakan min-max scaler"""
        # Konversi list of dict ke DataFrame untuk memudahkan normalisasi
        df = pd.DataFrame(data)
        
        # Kolom yang akan dinormalisasi
        cols = ['cost', 'clicks', 'impressions']
        
        # Simpan scaler untuk setiap kolom
        scalers = {}
        
        # Normalisasi setiap kolom
        for col in cols:
            if col in df.columns:
                # Buat scaler
                scaler = MinMaxScaler()
                # Reshape data untuk format yang dibutuhkan fit_transform
                values = df[col].values.reshape(-1, 1)
                # Fit dan transform
                normalized_values = scaler.fit_transform(values).flatten()
                # Tambahkan kolom hasil normalisasi
                norm_col = f"{col}_norm"
                df[norm_col] = normalized_values
                # Simpan scaler
                scalers[col] = scaler
        
        # Kembalikan ke format list of dict
        normalized_data = df.to_dict('records')
        
        return normalized_data, scalers

    def rank_ads(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Proses utama untuk ranking iklan menggunakan logika fuzzy"""
        # Jika data kosong, kembalikan list kosong
        if not data:
            return []
        
        # Normalisasi data
        normalized_data, _ = self.normalize_data(data)
        
        # Hitung ranking untuk setiap baris
        for row in normalized_data:
            norm_data = {
                'cost_norm': row.get('cost_norm', 0),
                'clicks_norm': row.get('clicks_norm', 0),
                'impressions_norm': row.get('impressions_norm', 0)
            }
            row['ranking'] = self.compute_ranking(norm_data)
        
        # Urutkan data berdasarkan ranking (tertinggi di atas)
        sorted_data = sorted(normalized_data, key=lambda x: x.get('ranking', 0), reverse=True)
        
        return sorted_data