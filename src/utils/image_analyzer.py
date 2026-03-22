#!/usr/bin/env python3
"""
Image Analysis Module
Handles image processing with OCR fallback for non-vision models
"""

import os
import base64
from typing import Dict, Any, Optional
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageAnalyzer:
    """
    Image analyzer with OCR support.
    Falls back to OCR when vision models are not available.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tesseract_config = self.config.get('tesseract_config', '--psm 6')
        self.canny_threshold1 = self.config.get('canny_threshold1', 50)
        self.canny_threshold2 = self.config.get('canny_threshold2', 150)
        
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available. Using PIL for image processing.")
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract not available. Text extraction will be limited.")
    
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze image using OCR (no vision model required).
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Analysis results with extracted text and structure
        """
        try:
            # Load image
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image not found: {image_path}"
                }
            
            # Extract text using OCR
            extracted_text = self._extract_text_ocr(image_path)
            
            # Analyze structure
            structure = self._analyze_structure(image_path)
            
            # Detect errors
            error_messages = self._detect_errors(extracted_text)
            
            return {
                "success": True,
                "extracted_text": extracted_text,
                "structure": structure,
                "error_messages": error_messages,
                "confidence": self._calculate_confidence(extracted_text),
                "ocr_used": True
            }
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_text_ocr(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        if not TESSERACT_AVAILABLE:
            return "OCR not available - install pytesseract"
        
        try:
            if PIL_AVAILABLE:
                image = Image.open(image_path)
                text = pytesseract.image_to_string(
                    image,
                    config=self.tesseract_config,
                    lang='eng+vie'
                )
                return text.strip()
            elif CV2_AVAILABLE:
                image = cv2.imread(image_path)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(
                    gray,
                    config=self.tesseract_config,
                    lang='eng+vie'
                )
                return text.strip()
            
            return "No image processing library available"
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    def _analyze_structure(self, image_path: str) -> Dict[str, Any]:
        """Analyze image structure (lines, shapes)"""
        if not CV2_AVAILABLE:
            return {"summary": "OpenCV not available for structure analysis"}
        
        try:
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, self.canny_threshold1, self.canny_threshold2)
            
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                                   minLineLength=30, maxLineGap=10)
            
            line_count = len(lines) if lines is not None else 0
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            return {
                "summary": f"Detected {line_count} lines and {len(contours)} contours",
                "lines": line_count,
                "contours": len(contours)
            }
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return {"summary": "Structure analysis failed"}
    
    def _detect_errors(self, text: str) -> list:
        """Detect error patterns in text"""
        error_patterns = [
            "error", "exception", "failed", "nullpointer", "null pointer",
            "timeout", "connection refused", "access denied", "not found",
            "undefined", "cannot read", "syntaxerror", "typeerror",
            "lỗi", "ngoại lệ", "thất bại"
        ]
        
        errors = []
        for line in text.split('\n'):
            line_lower = line.lower().strip()
            for pattern in error_patterns:
                if pattern in line_lower:
                    errors.append(line.strip())
                    break
        
        return errors
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence based on text extraction quality"""
        if not text:
            return 0.0
        
        char_count = len(text)
        word_count = len(text.split())
        
        confidence = min(char_count / 100, 1.0) * 0.7 + min(word_count / 20, 1.0) * 0.3
        return round(confidence, 2)


def analyze_screenshot(image_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to analyze a screenshot.
    
    This function uses OCR and does NOT require a vision-capable model.
    It works with any text-only LLM.
    
    Args:
        image_path: Path to the screenshot
        config: Optional configuration
        
    Returns:
        Analysis results
    """
    analyzer = ImageAnalyzer(config)
    return analyzer.analyze_image(image_path)


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from image using OCR.
    
    Args:
        image_path: Path to the image
        
    Returns:
        Extracted text
    """
    analyzer = ImageAnalyzer()
    result = analyzer.analyze_image(image_path)
    return result.get("extracted_text", "")


__all__ = ["ImageAnalyzer", "analyze_screenshot", "extract_text_from_image"]
