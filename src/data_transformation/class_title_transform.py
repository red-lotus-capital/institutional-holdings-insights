import pandas as pd
import re

class ClassTitleTransform:
    def __init__(self):
        pass
        
    def normalize_title(self, title):
        """Normalize title for better matching"""
        return ' '.join(str(title).upper().split())
    
    def transform(self, series):
        """
        Transform a pandas Series of class titles into standardized categories
        
        Parameters:
        -----------
        series : pd.Series
            Series containing security class titles
            
        Returns:
        --------
        pd.Series
            Series with standardized category names
        """
        return series.apply(self._categorize_single)
    
    def _categorize_single(self, title):
        """Categorize a single security title"""
        if pd.isna(title):
            return 'Unclassified Security'
            
        title_norm = self.normalize_title(title)
        
        # Expiring securities
        if '*W EXP' in title_norm or 'RIGHT' in title_norm and '99/99' not in title_norm:
            return 'Expiring Security - Rights & Warrants'
        
        # IBONDS
        if 'IBOND' in title_norm:
            return 'Target Maturity Bond ETF'
        
        # Notes (Treasury/Corporate)
        if title_norm.startswith('NOTE '):
            return 'Fixed Income Note'
        
        # Common Stock variations
        common_patterns = ['COM STK', 'COM SHS', 'COMMON STOCK', 'COMMON SHARES', 
                         'COMMON', 'COM NEW', 'COM PAR', 'COM NPV', 'COM UNIT', 'ORDINARY']
        if any(pattern in title_norm for pattern in common_patterns):
            if 'CL A' in title_norm or 'CLASS A' in title_norm or 'SER A' in title_norm:
                return 'Common Stock - Class A'
            elif 'CL B' in title_norm or 'CLASS B' in title_norm or 'SER B' in title_norm:
                return 'Common Stock - Class B'
            elif 'CL C' in title_norm or 'CLASS C' in title_norm or 'SER C' in title_norm:
                return 'Common Stock - Class C'
            else:
                return 'Common Stock'
        
        # Preferred Stock
        pfd_patterns = ['PFD', 'PREF', 'PREFERRED']
        if any(pattern in title_norm for pattern in pfd_patterns):
            return 'Preferred Stock'
        
        # ADR/ADS
        if 'ADR' in title_norm or 'ADS' in title_norm or 'SPON' in title_norm:
            return 'American Depositary Receipt'
        
        # Units
        if title_norm.startswith('UNIT') or ('UNIT' in title_norm and 'LP' in title_norm):
            return 'Partnership Unit'
        
        # Treasury Securities
        if any(word in title_norm for word in ['TREASURY', 'TREAS', 'T-BILL']):
            return 'US Treasury Security'
        
        # Municipal Bonds
        if 'MUNI' in title_norm or 'MUNICIPAL' in title_norm:
            return 'Municipal Bond ETF'
        
        # High Yield Bonds
        if 'HIGH YIELD' in title_norm or 'HIGH YLD' in title_norm or 'HI YLD' in title_norm:
            return 'High Yield Bond ETF'
        
        # Investment Grade
        if 'INVT GR' in title_norm or 'INVESTMENT GRADE' in title_norm or 'INV GR' in title_norm:
            return 'Investment Grade Bond ETF'
        
        # Bond maturity classifications
        if any(term in title_norm for term in ['SHORT TERM', 'SHORT-TERM', 'SHRT', 'SHORT DUR']):
            return 'Short Term Bond ETF'
        elif any(term in title_norm for term in ['INTERMEDIATE', 'INTERMED', 'INT-TERM']):
            return 'Intermediate Term Bond ETF'
        elif any(term in title_norm for term in ['LONG TERM', 'LONG-TERM', 'LT ', '20+', '25+']):
            return 'Long Term Bond ETF'
        
        # TIPS
        if 'TIPS' in title_norm or ('INFLATION' in title_norm and 'ETF' in title_norm):
            return 'Inflation Protected Bond ETF'
        
        # ESG/Sustainable
        if 'ESG' in title_norm or 'SUSTAINABLE' in title_norm or ('CLEAN' in title_norm and 'ETF' in title_norm):
            return 'ESG/Sustainable Equity ETF'
        
        # Geographic - China/Asia
        if any(region in title_norm for region in ['CHINA', 'ASIA', 'PACIFIC', 'HONG KONG', 
                                                    'TAIWAN', 'JAPAN', 'INDIA', 'KOREA']):
            return 'Asia Pacific Equity ETF'
        
        # Geographic - Europe
        if any(region in title_norm for region in ['EUROPE', 'EURO', 'EAFE', 'UK', 'GERMANY', 
                                                    'FRANCE', 'SPAIN', 'ITALY']):
            return 'European Equity ETF'
        
        # Geographic - Latin America
        if any(region in title_norm for region in ['LATIN', 'BRAZIL', 'MEXICO', 'CHILE']):
            return 'Latin America Equity ETF'
        
        # Geographic - Emerging Markets
        if 'EMERG' in title_norm or 'EM MKT' in title_norm or 'EM MK' in title_norm:
            return 'Emerging Markets Equity ETF'
        
        # Sector - Technology
        if any(tech in title_norm for tech in ['TECH', 'SEMICONDUCTOR', 'SOFTWARE', 'CYBER', 
                                                'CLOUD', 'AI', 'ARTIFICIAL']):
            return 'Technology Sector ETF'
        
        # Sector - Healthcare
        if any(health in title_norm for health in ['HEALTH', 'PHARMA', 'BIOTECH', 'MEDICAL']):
            return 'Healthcare Sector ETF'
        
        # Sector - Financials
        if any(fin in title_norm for fin in ['FINANC', 'BANK', 'BK ETF', 'INSURANCE']):
            return 'Financial Sector ETF'
        
        # Sector - Energy
        if 'ENERGY' in title_norm or 'OIL' in title_norm or 'GAS' in title_norm:
            return 'Energy Sector ETF'
        
        # Sector - Industrials
        if 'INDUST' in title_norm or 'AEROSPACE' in title_norm or 'DEFENSE' in title_norm:
            return 'Industrial Sector ETF'
        
        # Sector - Consumer Discretionary
        if 'CONSUM DIS' in title_norm or 'CONSUMER DIS' in title_norm:
            return 'Consumer Discretionary Sector ETF'
        
        # Sector - Consumer Staples
        if 'CONSUM STP' in title_norm or 'CONSUMER STP' in title_norm or 'CONSUM STAPLE' in title_norm:
            return 'Consumer Staples Sector ETF'
        
        # Sector - Utilities
        if 'UTIL' in title_norm and 'ETF' in title_norm:
            return 'Utilities Sector ETF'
        
        # Sector - Materials
        if 'MATERIAL' in title_norm or ('METAL' in title_norm and 'ETF' in title_norm):
            return 'Materials Sector ETF'
        
        # Sector - Communication Services
        if 'COMM' in title_norm and 'SVC' in title_norm:
            return 'Communication Services Sector ETF'
        
        # Sector - Real Estate
        if 'REAL EST' in title_norm or 'REIT' in title_norm:
            return 'Real Estate Equity ETF'
        
        # Dividend focused
        if 'DIV' in title_norm and 'ETF' in title_norm:
            return 'Dividend Focused Equity ETF'
        
        # Growth
        if ('GROW' in title_norm or 'GRW' in title_norm or 'GWT' in title_norm) and 'ETF' in title_norm:
            return 'Growth Equity ETF'
        
        # Value
        if ('VALUE' in title_norm or 'VAL' in title_norm or 'VL ' in title_norm) and 'ETF' in title_norm:
            return 'Value Equity ETF'
        
        # Momentum
        if ('MOMENT' in title_norm or 'MOMNT' in title_norm) and 'ETF' in title_norm:
            return 'Momentum Equity ETF'
        
        # Low Volatility
        if ('LOW VOL' in title_norm or 'MIN VOL' in title_norm) and 'ETF' in title_norm:
            return 'Low Volatility Equity ETF'
        
        # Quality
        if 'QUAL' in title_norm and 'ETF' in title_norm:
            return 'Quality Equity ETF'
        
        # US Equity Size Classifications
        if any(size in title_norm for size in ['LARGE CAP', 'LRG CAP', 'LCAP', 'MEGA CAP', 
                                                 'S&P 500', 'S&P500', 'RUSSELL 1000']):
            return 'US Large Cap Equity ETF'
        elif any(size in title_norm for size in ['MID CAP', 'MDCP', 'MIDCAP', 'S&P 400', 
                                                   'RUSSELL MID']):
            return 'US Mid Cap Equity ETF'
        elif any(size in title_norm for size in ['SMALL CAP', 'SML CAP', 'SMCP', 'SMLCP', 
                                                   'S&P 600', 'RUSSELL 2000']):
            return 'US Small Cap Equity ETF'
        
        # International Developed
        if any(intl in title_norm for intl in ['INTL', 'INTERNATIONAL', 'GLOBAL', 'WORLD', 
                                                'DEVELOPED']) and 'ETF' in title_norm:
            return 'International Developed Markets Equity ETF'
        
        # Bond ETFs (general)
        if any(bond in title_norm for bond in ['BOND', 'BD ETF', 'CORP BD', 'AGGREGATE']) and 'ETF' in title_norm:
            return 'Fixed Income Bond ETF'
        
        # Commodity
        if any(comm in title_norm for comm in ['GOLD', 'SILVER', 'COMMODITY', 'METAL', 
                                                'PLATINUM', 'PALLADIUM']):
            return 'Commodity ETF'
        
        # Shares/Stock indicators without specific classification
        if any(share in title_norm for share in ['SHS', 'SHARES', 'STK', 'STOCK', 'CAP STK']):
            return 'Equity Security'
        
        # ETF catch-all
        if 'ETF' in title_norm or 'INDEX' in title_norm or 'FUND' in title_norm:
            return 'Exchange Traded Fund'
        
        # Bond/Debt instruments
        if any(debt in title_norm for debt in ['BOND', 'NOTE', 'DEBT', 'DEBENTURE']):
            return 'Fixed Income Security'
        
        # If nothing matched
        return 'Unclassified Security'

