#!/usr/bin/env python3

import os
import logging
import tempfile
import json
from pdfservices.operation.auth.credentials import Credentials
from pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from pdfservices.operation.execution_context import ExecutionContext
from pdfservices.operation.io.file_ref import FileRef
from pdfservices.operation.pdfops.export_pdf_operation import ExportPDFOperation
from pdfservices.operation.pdfops.options.exportpdf.export_pdf_options import ExportPDFOptions
from pdfservices.operation.pdfops.options.exportpdf.export_pdf_target_format import ExportPDFTargetFormat

# Set up logging
logger = logging.getLogger('adobe_pdf_services')

# Path to credentials file
CREDENTIALS_FILE = '/app/config/pdfservices-api-credentials.json'

def get_execution_context():
    """Create and return an execution context using credentials from JSON file."""
    try:
        # Load credentials from JSON file
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                credentials_json = json.load(f)
                
            client_id = credentials_json['client_credentials']['client_id']
            client_secret = credentials_json['client_credentials']['client_secret']
            
            # Create credentials using client_id and client_secret
            credentials = Credentials.service_account_credentials_builder() \
                .with_client_id(client_id) \
                .with_client_secret(client_secret) \
                .build()
                
            return ExecutionContext.create(credentials)
        else:
            raise FileNotFoundError(f"Credentials file not found: {CREDENTIALS_FILE}")
    
    except Exception as e:
        logger.error(f"Error creating execution context: {e}")
        raise

def convert_pdf_to_excel(pdf_path, excel_path):
    """
    Convert a PDF to Excel using Adobe PDF Services API.
    
    Args:
        pdf_path (str): Path to the source PDF file
        excel_path (str): Path where the Excel file should be saved
        
    Returns:
        bool: True if conversion was successful, False otherwise
    """
    try:
        # Create an execution context using credentials
        execution_context = get_execution_context()
        
        # Create a new operation instance
        export_pdf_operation = ExportPDFOperation.create_new()
        
        # Set operation input from a source file
        source = FileRef.create_from_local_file(pdf_path)
        export_pdf_operation.set_input(source)
        
        # Configure the export options
        export_pdf_options = ExportPDFOptions.xlsx()
        # Note: Adobe API doesn't allow direct control over thousands/decimal separators
        # This will be handled in post-processing if needed
        export_pdf_operation.set_options(export_pdf_options)
        
        # Execute the operation
        logger.info(f"Converting PDF to Excel: {pdf_path}")
        result = export_pdf_operation.execute(execution_context)
        
        # Save the result to the specified path
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            result.save_as(temp_file.name)
            
            # Check if we need to do any post-processing for comma/dot formatting
            # This would need custom implementation since Adobe API doesn't 
            # directly support setting these separators
            
            # For now, just copy the file to the destination
            import shutil
            shutil.copy2(temp_file.name, excel_path)
            os.unlink(temp_file.name)
        
        logger.info(f"Successfully converted PDF to Excel: {excel_path}")
        return True
        
    except ServiceApiException as e:
        logger.error(f"Adobe API error: {e.message}")
        logger.error(f"Response code: {e.get_error_response().statusCode}")
        logger.error(f"Response body: {e.get_error_response().message}")
        return False
    except ServiceUsageException as e:
        logger.error(f"Adobe service usage error: {e.message}")
        return False
    except SdkException as e:
        logger.error(f"Adobe SDK error: {e.message}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in PDF to Excel conversion: {e}")
        return False