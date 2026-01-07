"""
Paprasta cache sistema PDF failų apdorojimo rezultatams.
"""
import os
import json
import hashlib
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path


class SimpleFileCache:
    """Paprasta failų cache sistema."""
    
    def __init__(self, cache_dir: str = "cache", max_age_hours: int = 24):
        """
        Inicializuoja cache sistemą.
        
        Args:
            cache_dir: Cache katalogo pavadinimas
            max_age_hours: Maksimalus cache įrašo amžius valandomis
        """
        self.cache_dir = Path(cache_dir)
        self.max_age_seconds = max_age_hours * 3600
        self.cache_dir.mkdir(exist_ok=True)
        
        # Išvalome senus cache failus paleidimo metu
        self._cleanup_old_cache()
    
    def _get_file_hash(self, file_path: str) -> str:
        """Apskaičiuoja failo identifikatorių be failo skaitymo."""
        try:
            # Naudojame failo pavadinimą ir modifikacijos laiką vietoj hash
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                file_id = f"{os.path.basename(file_path)}_{int(stat.st_mtime)}_{stat.st_size}"
                return hashlib.md5(file_id.encode()).hexdigest()
            else:
                # Sudarome deterministinį hash net jei kelias nėra realus failas
                return hashlib.md5(str(file_path).encode()).hexdigest()
        except Exception as e:
            logging.warning("Nepavyko apskaičiuoti failo hash: %s", e)
            return str(time.time())  # Fallback
    
    def _get_cache_path(self, file_path: str) -> Path:
        """Grąžina cache failo kelią."""
        file_hash = self._get_file_hash(file_path)
        cache_filename = f"cache_{file_hash}.json"
        return self.cache_dir / cache_filename
    
    def get(self, file_path: str) -> Optional[Dict[Any, Any]]:
        """
        Gauna duomenis iš cache.
        
        Args:
            file_path: Originalaus failo kelias
            
        Returns:
            Cache duomenys arba None jei nerastas/pasenęs
        """
        cache_path = self._get_cache_path(file_path)
        
        if not cache_path.exists():
            logging.debug("Cache nerastas: %s", cache_path)
            return None
        
        try:
            # Tikriname cache amžių
            cache_age = time.time() - cache_path.stat().st_mtime
            if cache_age > self.max_age_seconds:
                logging.info("Cache pasenęs, šaliname: %s", cache_path)
                cache_path.unlink()
                return None
            
            # Skaitome cache duomenis
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logging.info("Cache hit: %s (amžius: %.1f val.)", file_path, cache_age / 3600)
            return data
            
        except Exception as e:
            logging.warning("Klaida skaitant cache: %s", e)
            # Šaliname sugadintą cache failą
            try:
                cache_path.unlink()
            except:
                pass
            return None
    
    def set(self, file_path: str, data: Dict[Any, Any]) -> None:
        """
        Išsaugo duomenis į cache.
        
        Args:
            file_path: Originalaus failo kelias
            data: Išsaugomi duomenys
        """
        cache_path = self._get_cache_path(file_path)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info("Duomenys išsaugoti į cache: %s", file_path)
            
        except Exception as e:
            logging.error("Klaida išsaugant į cache: %s", e)
    
    def clear(self) -> int:
        """
        Išvalo visą cache.
        
        Returns:
            Pašalintų failų skaičius
        """
        removed_count = 0
        try:
            for cache_file in self.cache_dir.glob("cache_*.json"):
                cache_file.unlink()
                removed_count += 1
            
            logging.info("Cache išvalytas: pašalinta %d failų", removed_count)
            
        except Exception as e:
            logging.error("Klaida valant cache: %s", e)
        
        return removed_count
    
    def _cleanup_old_cache(self) -> None:
        """Išvalo senus cache failus."""
        try:
            current_time = time.time()
            removed_count = 0
            
            for cache_file in self.cache_dir.glob("cache_*.json"):
                cache_age = current_time - cache_file.stat().st_mtime
                if cache_age > self.max_age_seconds:
                    cache_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                logging.info("Automatiškai pašalinta %d pasenusių cache failų", removed_count)
                
        except Exception as e:
            logging.warning("Klaida valant senus cache failus: %s", e)
    
    def get_stats(self) -> Dict[str, Any]:
        """Grąžina cache statistiką."""
        try:
            cache_files = list(self.cache_dir.glob("cache_*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                "cache_files_count": len(cache_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_dir": str(self.cache_dir),
                "max_age_hours": self.max_age_seconds / 3600
            }
        except Exception as e:
            logging.error("Klaida gaunant cache statistiką: %s", e)
            return {"error": str(e)}


# Globalus cache objektas
pdf_cache = SimpleFileCache()