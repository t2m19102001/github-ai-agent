#!/usr/bin/env python3
"""
Test Image Agent - Phase 5
Tests for multi-modal image processing capabilities
"""

import os
import sys
import unittest
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agents.image_agent import ImageAgent
from src.rag.vector_store import VectorStore
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TestImageAgent(unittest.TestCase):
    """Test cases for ImageAgent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.agent = ImageAgent()
        self.test_data_dir = os.path.join(project_root, "tests", "data", "images")
        
        # Create test data directory
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Create test images
        self.create_test_images()
    
    def create_test_images(self):
        """Create test images for testing"""
        # Create a simple diagram image
        diagram_img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(diagram_img)
        
        # Draw rectangles (boxes)
        draw.rectangle([50, 50, 150, 100], outline='black', width=2)
        draw.rectangle([200, 50, 300, 100], outline='black', width=2)
        draw.rectangle([100, 150, 200, 200], outline='black', width=2)
        
        # Draw arrows (connections)
        draw.line([100, 75, 200, 75], fill='black', width=2)
        draw.line([250, 75, 150, 175], fill='black', width=2)
        draw.line([150, 175, 100, 125], fill='black', width=2)
        
        # Add text
        try:
            # Try to use a simple font
            font = ImageFont.load_default()
            draw.text((55, 60), "Module A", fill='black', font=font)
            draw.text((205, 60), "Module B", fill='black', font=font)
            draw.text((105, 160), "Module C", fill='black', font=font)
        except:
            # Fallback if font loading fails
            pass
        
        diagram_path = os.path.join(self.test_data_dir, "test_diagram.png")
        diagram_img.save(diagram_path)
        
        # Create a screenshot with error message
        error_img = Image.new('RGB', (600, 400), color='white')
        draw = ImageDraw.Draw(error_img)
        
        # Draw window frame
        draw.rectangle([50, 50, 550, 350], outline='black', width=2)
        
        # Add error text
        error_text = "Error: NullPointerException at line 42"
        draw.text((60, 60), error_text, fill='red')
        draw.text((60, 80), "at com.example.UserService.getUser(UserService.java:42)", fill='black')
        
        error_path = os.path.join(self.test_data_dir, "error_screenshot.png")
        error_img.save(error_path)
        
        # Create a simple text image
        text_img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(text_img)
        draw.text((10, 10), "This is a test image for OCR", fill='black')
        
        text_path = os.path.join(self.test_data_dir, "test_text.png")
        text_img.save(text_path)
        
        logger.info(f"Created test images in {self.test_data_dir}")
    
    def test_image_agent_initialization(self):
        """Test ImageAgent initialization"""
        agent = ImageAgent()
        self.assertEqual(agent.name, "ImageAgent")
        self.assertIn("ocr", agent.capabilities)
        self.assertIn("diagram_analysis", agent.capabilities)
        self.assertIn("screenshot_analysis", agent.capabilities)
        
        # Test with RAG store
        vector_store = VectorStore(dimension=128, storage_path=":memory:")
        agent_with_rag = ImageAgent(rag_store=vector_store)
        self.assertIsNotNone(agent_with_rag.rag_store)
        
        logger.info("✅ ImageAgent initialization tests passed")
    
    def test_ocr_processing(self):
        """Test OCR text extraction"""
        text_image_path = os.path.join(self.test_data_dir, "test_text.png")
        
        result = self.agent.process(text_image_path)
        
        self.assertTrue(result.get("success", False))
        self.assertIn("extracted_text", result)
        self.assertIn("This is a test image for OCR", result["extracted_text"])
        self.assertGreater(result.get("confidence_score", 0), 0)
        
        logger.info("✅ OCR processing test passed")
    
    def test_diagram_analysis(self):
        """Test diagram structure analysis"""
        diagram_path = os.path.join(self.test_data_dir, "test_diagram.png")
        
        result = self.agent.process(diagram_path)
        
        self.assertTrue(result.get("success", False))
        self.assertIn("diagram_info", result)
        self.assertIn("structural_elements", result)
        
        # Should detect structural elements
        elements = result.get("structural_elements", [])
        self.assertGreater(len(elements), 0)
        
        # Should detect connections
        diagram_info = result.get("diagram_info", "")
        self.assertIn("Detected", diagram_info)
        self.assertIn("elements", diagram_info)
        
        logger.info("✅ Diagram analysis test passed")
    
    def test_error_detection(self):
        """Test error message detection in screenshots"""
        error_path = os.path.join(self.test_data_dir, "error_screenshot.png")
        
        result = self.agent.analyze_screenshot(error_path)
        
        self.assertTrue(result.get("success", False))
        
        # Should detect error messages
        error_messages = result.get("error_messages", [])
        self.assertGreater(len(error_messages), 0)
        
        # Should identify bug type
        bug_analysis = result.get("bug_analysis", {})
        self.assertTrue(bug_analysis.get("has_errors", False))
        self.assertIn("error_count", bug_analysis)
        self.assertIn("likely_bug_type", bug_analysis)
        
        logger.info("✅ Error detection test passed")
    
    def test_image_input_formats(self):
        """Test different image input formats"""
        # Test with file path
        image_path = os.path.join(self.test_data_dir, "test_text.png")
        result1 = self.agent.process(image_path)
        self.assertTrue(result1.get("success", False))
        
        # Test with numpy array
        image = Image.open(image_path)
        img_array = np.array(image)
        result2 = self.agent.process(img_array)
        self.assertTrue(result2.get("success", False))
        
        # Test with bytes
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        result3 = self.agent.process(img_bytes)
        self.assertTrue(result3.get("success", False))
        
        logger.info("✅ Image input format tests passed")
    
    def test_rag_integration(self):
        """Test RAG integration with image processing"""
        # Create mock vector store
        vector_store = VectorStore(dimension=128, storage_path=":memory:")
        
        # Add some test documents
        test_docs = [
            "NullPointerException occurs when trying to access a null object",
            "Always check for null values before accessing object methods",
            "Use Optional types to handle potentially null values"
        ]
        
        for i, doc in enumerate(test_docs):
            embedding = np.random.rand(128)
            vector_store.add_document(f"doc_{i}", doc, embedding, {"type": "error_handling"})
        
        # Create agent with RAG
        agent_with_rag = ImageAgent(rag_store=vector_store)
        
        # Process error screenshot
        error_path = os.path.join(self.test_data_dir, "error_screenshot.png")
        result = agent_with_rag.process(error_path)
        
        self.assertTrue(result.get("success", False))
        self.assertIn("related_docs", result)
        
        # Should find related documentation
        related_docs = result.get("related_docs", [])
        self.assertGreater(len(related_docs), 0)
        
        logger.info("✅ RAG integration test passed")
    
    def test_confidence_scoring(self):
        """Test confidence score calculation"""
        text_image_path = os.path.join(self.test_data_dir, "test_text.png")
        result = self.agent.process(text_image_path)
        
        confidence = result.get("confidence_score", 0)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # Image with more content should have higher confidence
        diagram_path = os.path.join(self.test_data_dir, "test_diagram.png")
        diagram_result = self.agent.process(diagram_path)
        diagram_confidence = diagram_result.get("confidence_score", 0)
        
        # Diagram should have higher confidence due to structural elements
        self.assertGreaterEqual(diagram_confidence, confidence)
        
        logger.info("✅ Confidence scoring test passed")
    
    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test with non-existent file
        result = self.agent.process("non_existent.png")
        self.assertFalse(result.get("success", True))
        self.assertIn("error", result)
        
        # Test with invalid data type
        result = self.agent.process(12345)
        self.assertFalse(result.get("success", True))
        self.assertIn("error", result)
        
        logger.info("✅ Error handling tests passed")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)
            logger.info(f"Cleaned up test directory: {self.test_data_dir}")

def run_image_agent_tests():
    """Run all ImageAgent tests"""
    logger.info("🧪 Starting ImageAgent Tests...")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestImageAgent)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report results
    if result.wasSuccessful():
        logger.info("✅ All ImageAgent tests passed!")
        return True
    else:
        logger.error(f"❌ {len(result.failures)} test(s) failed")
        for failure in result.failures:
            logger.error(f"FAILED: {failure[0]} - {failure[1]}")
        return False

if __name__ == "__main__":
    success = run_image_agent_tests()
    sys.exit(0 if success else 1)
