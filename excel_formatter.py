#!/usr/bin/env python3

import os
import re
import logging
import openpyxl
from openpyxl.styles import Font, Alignment

# Set up logging
logger = logging.getLogger('excel_formatter')

def format_excel_numbers(excel_path):
    """
    Post-process Excel file from Adobe API to ensure proper number formatting:
    - "," as thousands separator
    - "." as decimal separator
    
    Returns:
        bool: True if formatting was successful, False otherwise
    """
    try:
        logger.info(f"Post-processing Excel file: {excel_path}")
        
        # Load the workbook
        workbook = openpyxl.load_workbook(excel_path)
        
        # Regex pattern to identify numbers (with or without commas/periods)
        # Matches:
        # - Integers: 1234
        # - Decimals: 1234.56
        # - With commas: 1,234.56
        number_pattern = re.compile(r'^-?\d{1,3}(,\d{3})*(\.\d+)?$|^-?\d+(\.\d+)?$')
        
        # Process each worksheet
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            
            # Process each cell
            for row in worksheet.iter_rows():
                for cell in row:
                    # Skip empty cells
                    if not cell.value:
                        continue
                    
                    # Handle string cells that might contain numbers
                    if isinstance(cell.value, str):
                        # Remove any existing commas
                        str_value = cell.value.strip()
                        
                        # If it's a number in string format
                        if number_pattern.match(str_value):
                            # Remove existing commas for processing
                            cleaned = str_value.replace(',', '')
                            
                            try:
                                if '.' in cleaned:
                                    # It's a decimal number
                                    cell.value = float(cleaned)
                                    cell.number_format = '#,##0.00'  # Comma as thousands, dot as decimal
                                else:
                                    # It's an integer
                                    cell.value = int(cleaned)
                                    cell.number_format = '#,##0'  # Comma as thousands
                            except ValueError:
                                pass  # Keep as string if conversion fails
                    
                    # For numerical cells, ensure proper formatting
                    elif isinstance(cell.value, int):
                        cell.number_format = '#,##0'  # Comma as thousands
                    elif isinstance(cell.value, float):
                        cell.number_format = '#,##0.00'  # Comma as thousands, dot as decimal
        
        # Save the workbook
        workbook.save(excel_path)
        logger.info(f"Successfully formatted Excel file: {excel_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error formatting Excel file: {e}")
        return False

# Enhance Adobe conversion function to include post-processing
def enhanced_adobe_conversion(pdf_path, excel_path):
    """
    Convert PDF to Excel using Adobe API and then apply number formatting.
    """
    import adobe_utils
    
    # First, use Adobe API to convert
    success = adobe_utils.convert_pdf_to_excel(pdf_path, excel_path)
    
    if success:
        # Apply number formatting
        format_success = format_excel_numbers(excel_path)
        if not format_success:
            logger.warning(f"Adobe conversion succeeded but number formatting failed: {excel_path}")
    
    return success