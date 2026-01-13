"""Local file storage utilities."""

import os
import shutil
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LocalStorage:
    """Local file storage handler."""
    
    def __init__(self, base_path: str = "./storage"):
        """
        Initialize local storage.
        
        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        file_data: bytes | BinaryIO,
        filename: str,
        subfolder: Optional[str] = None
    ) -> Path:
        """
        Save file to local storage.
        
        Args:
            file_data: File data (bytes or file-like object)
            filename: Name of the file
            subfolder: Optional subfolder path
            
        Returns:
            Path to saved file
        """
        # Create subfolder if specified
        if subfolder:
            save_path = self.base_path / subfolder
        else:
            save_path = self.base_path
        
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        file_path = save_path / filename
        
        # Write file
        if isinstance(file_data, bytes):
            file_path.write_bytes(file_data)
        else:
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
        
        logger.info(f"Saved file to {file_path}")
        return file_path
    
    def read(self, filename: str, subfolder: Optional[str] = None) -> bytes:
        """
        Read file from local storage.
        
        Args:
            filename: Name of the file
            subfolder: Optional subfolder path
            
        Returns:
            File contents as bytes
        """
        if subfolder:
            file_path = self.base_path / subfolder / filename
        else:
            file_path = self.base_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return file_path.read_bytes()
    
    def delete(self, filename: str, subfolder: Optional[str] = None) -> bool:
        """
        Delete file from local storage.
        
        Args:
            filename: Name of the file
            subfolder: Optional subfolder path
            
        Returns:
            True if deleted successfully
        """
        if subfolder:
            file_path = self.base_path / subfolder / filename
        else:
            file_path = self.base_path / filename
        
        if not file_path.exists():
            return False
        
        file_path.unlink()
        logger.info(f"Deleted file: {file_path}")
        return True
    
    def exists(self, filename: str, subfolder: Optional[str] = None) -> bool:
        """
        Check if file exists in local storage.
        
        Args:
            filename: Name of the file
            subfolder: Optional subfolder path
            
        Returns:
            True if file exists
        """
        if subfolder:
            file_path = self.base_path / subfolder / filename
        else:
            file_path = self.base_path / filename
        
        return file_path.exists()
    
    def get_size(self, filename: str, subfolder: Optional[str] = None) -> int:
        """
        Get file size in bytes.
        
        Args:
            filename: Name of the file
            subfolder: Optional subfolder path
            
        Returns:
            File size in bytes
        """
        if subfolder:
            file_path = self.base_path / subfolder / filename
        else:
            file_path = self.base_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return file_path.stat().st_size
    
    def list_files(self, subfolder: Optional[str] = None) -> list[str]:
        """
        List all files in storage.
        
        Args:
            subfolder: Optional subfolder path
            
        Returns:
            List of filenames
        """
        if subfolder:
            search_path = self.base_path / subfolder
        else:
            search_path = self.base_path
        
        if not search_path.exists():
            return []
        
        return [f.name for f in search_path.iterdir() if f.is_file()]
    
    def get_url(self, filename: str, subfolder: Optional[str] = None) -> str:
        """
        Get local file URL/path.
        
        Args:
            filename: Name of the file
            subfolder: Optional subfolder path
            
        Returns:
            File path as string
        """
        if subfolder:
            return str(self.base_path / subfolder / filename)
        return str(self.base_path / filename)
    
    def copy(
        self,
        source_filename: str,
        dest_filename: str,
        source_subfolder: Optional[str] = None,
        dest_subfolder: Optional[str] = None
    ) -> Path:
        """
        Copy file within storage.
        
        Args:
            source_filename: Source filename
            dest_filename: Destination filename
            source_subfolder: Source subfolder
            dest_subfolder: Destination subfolder
            
        Returns:
            Path to copied file
        """
        # Read source file
        data = self.read(source_filename, source_subfolder)
        
        # Save to destination
        return self.save(data, dest_filename, dest_subfolder)
    
    def move(
        self,
        source_filename: str,
        dest_filename: str,
        source_subfolder: Optional[str] = None,
        dest_subfolder: Optional[str] = None
    ) -> Path:
        """
        Move file within storage.
        
        Args:
            source_filename: Source filename
            dest_filename: Destination filename
            source_subfolder: Source subfolder
            dest_subfolder: Destination subfolder
            
        Returns:
            Path to moved file
        """
        # Copy to destination
        new_path = self.copy(
            source_filename,
            dest_filename,
            source_subfolder,
            dest_subfolder
        )
        
        # Delete source
        self.delete(source_filename, source_subfolder)
        
        return new_path
