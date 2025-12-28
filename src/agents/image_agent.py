#!/usr/bin/env python3
"""
Image Agent Module - Phase 5
Multi-modal agent for processing images, diagrams, and screenshots
"""

import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
import io
import base64
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from src.agents.base_agent import BaseAgent
from src.rag.vector_store import VectorStore
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ImageAnalysisResult:
    """Result from image analysis"""
    extracted_text: str
    diagram_info: str
    error_messages: List[str]
    structural_elements: List[Dict[str, Any]]
    confidence_score: float
    related_docs: List[Any] = None

class ImageAgent:
    """Multi-modal agent for image processing and analysis"""
    
    def __init__(self, rag_store: Optional[VectorStore] = None, config: Dict[str, Any] = None):
        self.rag_store = rag_store
        self.config = config or {}
        
        # Agent properties
        self.name = "ImageAgent"
        self.description = "Multi-modal agent for processing images, diagrams, and screenshots"
        self.capabilities = ["ocr", "diagram_analysis", "screenshot_analysis", "bug_detection"]
        
        # Configure Tesseract
        self.tesseract_config = self.config.get('tesseract_config', '--psm 6')
        
        # OpenCV parameters
        self.canny_threshold1 = self.config.get('canny_threshold1', 50)
        self.canny_threshold2 = self.config.get('canny_threshold2', 150)
        
        logger.info(f"Initialized ImageAgent with RAG: {rag_store is not None}")
    
    def process(self, input_data: Union[str, bytes, np.ndarray]) -> Dict[str, Any]:
        """
        Process image and extract information
        
        Args:
            input_data: Image path, bytes, or numpy array
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Load and preprocess image
            image = self._load_image(input_data)
            if image is None:
                return self._create_error_result("Failed to load image")
            
            # Extract text using OCR
            extracted_text = self._extract_text_ocr(image)
            
            # Analyze image structure
            structural_analysis = self._analyze_image_structure(image)
            
            # Detect error messages in text
            error_messages = self._detect_error_messages(extracted_text)
            
            # Search for related documents if RAG is available
            related_docs = []
            if self.rag_store and extracted_text.strip():
                related_docs = self._search_related_docs(extracted_text)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(extracted_text, structural_analysis)
            
            # Create result
            result = {
                "agent": self.name,
                "success": True,
                "extracted_text": extracted_text,
                "diagram_info": structural_analysis["summary"],
                "structural_elements": structural_analysis["elements"],
                "error_messages": error_messages,
                "confidence_score": confidence,
                "related_docs": related_docs,
                "image_metadata": {
                    "shape": image.shape if hasattr(image, 'shape') else None,
                    "channels": len(image.shape) if hasattr(image, 'shape') and len(image.shape) == 3 else 1
                }
            }
            
            logger.info(f"Image analysis completed with confidence: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return self._create_error_result(str(e))
    
    def _load_image(self, input_data: Union[str, bytes, np.ndarray]) -> Optional[np.ndarray]:
        """Load image from various input formats"""
        try:
            if isinstance(input_data, str):
                # File path
                if not os.path.exists(input_data):
                    logger.error(f"Image file not found: {input_data}")
                    return None
                image = cv2.imread(input_data)
                
            elif isinstance(input_data, bytes):
                # Raw bytes
                nparr = np.frombuffer(input_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
            elif isinstance(input_data, np.ndarray):
                # Already numpy array
                image = input_data
                
            else:
                logger.error(f"Unsupported input type: {type(input_data)}")
                return None
            
            return image if image is not None else None
            
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return None
    
    def _extract_text_ocr(self, image: np.ndarray) -> str:
        """Extract text from image using OCR"""
        try:
            # Convert to PIL Image for Tesseract
            if len(image.shape) == 3:
                # Convert BGR to RGB
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            pil_image = Image.fromarray(image_rgb)
            
            # Extract text
            text = pytesseract.image_to_string(
                pil_image, 
                config=self.tesseract_config,
                lang='eng+vie'  # Support English and Vietnamese
            )
            
            logger.info(f"OCR extracted {len(text)} characters")
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    def _analyze_image_structure(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze image structure for diagrams and flowcharts"""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Edge detection
            edges = cv2.Canny(gray, self.canny_threshold1, self.canny_threshold2)
            
            # Find contours (structural elements)
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze contours
            elements = []
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area < 100:  # Skip small elements
                    continue
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Classify shape
                shape_type = self._classify_shape(contour)
                
                elements.append({
                    "id": i,
                    "type": shape_type,
                    "position": {"x": int(x), "y": int(y)},
                    "size": {"width": int(w), "height": int(h)},
                    "area": float(area)
                })
            
            # Detect lines (arrows, connections)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
            
            summary = f"Detected {len(elements)} structural elements and {len(lines) if lines is not None else 0} connections"
            
            return {
                "summary": summary,
                "elements": elements,
                "connections": [{"start": [int(x1), int(y1)], "end": [int(x2), int(y2)]} 
                              for x1, y1, x2, y2 in lines] if lines is not None else []
            }
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return {"summary": "Structure analysis failed", "elements": [], "connections": []}
    
    def _classify_shape(self, contour) -> str:
        """Classify shape based on contour properties"""
        try:
            # Approximate contour
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Classify based on number of vertices
            vertices = len(approx)
            
            if vertices == 3:
                return "triangle"
            elif vertices == 4:
                # Check if it's a square or rectangle
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = float(w) / h
                if 0.95 <= aspect_ratio <= 1.05:
                    return "square"
                else:
                    return "rectangle"
            elif vertices > 4:
                return "circle_or_ellipse"
            else:
                return "unknown_shape"
                
        except:
            return "unknown_shape"
    
    def _detect_error_messages(self, text: str) -> List[str]:
        """Detect error messages in extracted text"""
        if not text:
            return []
        
        error_patterns = [
            "error", "exception", "failed", "nullpointer", "null pointer",
            "timeout", "connection refused", "access denied", "not found",
            "lỗi", "ngoại lệ", "thất bại", "không tìm thấy"
        ]
        
        error_messages = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            for pattern in error_patterns:
                if pattern in line_lower:
                    error_messages.append(line.strip())
                    break
        
        return error_messages
    
    def _search_related_docs(self, text: str) -> List[Any]:
        """Search for related documents using RAG"""
        try:
            # Generate simple embedding for demo
            # In production, use proper embedding model
            embedding = np.random.rand(128)
            
            # Search in vector store
            results = self.rag_store.search(embedding, k=3)
            
            return [
                {
                    "content": result.document.content,
                    "score": result.score,
                    "metadata": result.document.metadata
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
    
    def _calculate_confidence(self, text: str, structural_analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis"""
        try:
            # Base confidence from text extraction
            text_confidence = min(len(text) / 100, 1.0) if text else 0.0
            
            # Confidence from structural analysis
            elements_count = len(structural_analysis.get("elements", []))
            structure_confidence = min(elements_count / 10, 1.0)
            
            # Combined confidence
            overall_confidence = (text_confidence * 0.6) + (structure_confidence * 0.4)
            
            return round(overall_confidence, 2)
            
        except:
            return 0.0
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            "agent": self.name,
            "success": False,
            "error": error_message,
            "extracted_text": "",
            "diagram_info": "",
            "error_messages": [],
            "confidence_score": 0.0,
            "related_docs": []
        }
    
    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """Specialized method for analyzing bug screenshots"""
        result = self.process(image_path)
        
        if result.get("success"):
            # Add screenshot-specific analysis
            error_messages = result.get("error_messages", [])
            if error_messages:
                result["bug_analysis"] = {
                    "has_errors": True,
                    "error_count": len(error_messages),
                    "likely_bug_type": self._classify_bug_type(error_messages),
                    "suggested_fixes": self._suggest_fixes(error_messages)
                }
            else:
                result["bug_analysis"] = {
                    "has_errors": False,
                    "suggestion": "No obvious errors detected in screenshot"
                }
        
        return result
    
    def _classify_bug_type(self, error_messages: List[str]) -> str:
        """Classify bug type based on error messages"""
        error_text = " ".join(error_messages).lower()
        
        if "null" in error_text or "pointer" in error_text:
            return "Null Pointer Exception"
        elif "connection" in error_text or "network" in error_text:
            return "Network/Connection Error"
        elif "timeout" in error_text:
            return "Timeout Error"
        elif "access" in error_text or "permission" in error_text:
            return "Access/Permission Error"
        elif "not found" in error_text or "404" in error_text:
            return "Not Found Error"
        else:
            return "General Error"
    
    def _suggest_fixes(self, error_messages: List[str]) -> List[str]:
        """Suggest fixes based on error messages"""
        fixes = []
        error_text = " ".join(error_messages).lower()
        
        if "null" in error_text:
            fixes.append("Add null checks before accessing variables")
        if "connection" in error_text:
            fixes.append("Check network connectivity and server status")
        if "timeout" in error_text:
            fixes.append("Increase timeout values or optimize performance")
        if "access" in error_text:
            fixes.append("Verify user permissions and authentication")
        if "not found" in error_text:
            fixes.append("Check file paths and resource availability")
        
        return fixes if fixes else ["Review error logs for more details"]
