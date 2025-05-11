#!/usr/bin/env python3

import os
import logging
import json
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import ExportPDFParams
from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import ExportPDFTargetFormat
from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult

# Set up logging
logger = logging.getLogger('adobe_pdf_services')

# Path to credentials file
CREDENTIALS_FILE = '/app/config/pdfservices-api-credentials.json'

def convert_pdf_to_excel(pdf_path, excel_path):
    """
    Convert a PDF to Excel using Adobe PDF Services API v4.1.0.
    
    Args:
        pdf_path (str): Path to the source PDF file
        excel_path (str): Path where the Excel file should be saved
        
    Returns:
        bool: True if conversion was successful, False otherwise
    """
    try:
        # Read PDF content
        with open(pdf_path, 'rb') as file:
            input_stream = file.read()
        
        # Load credentials from JSON file
        with open(CREDENTIALS_FILE, 'r') as f:
            credentials_json = json.load(f)
        
        # Create credentials instance
        credentials = ServicePrincipalCredentials(
            client_id=credentials_json['client_credentials']['client_id'],
            client_secret=credentials_json['client_credentials']['client_secret']
        )
        
        # Create PDF Services instance
        pdf_services = PDFServices(credentials=credentials)
        
        # Create asset from source file and upload
        input_asset = pdf_services.upload(
            input_stream=input_stream, 
            mime_type=PDFServicesMediaType.PDF
        )
        
        # Create parameters for Excel export
        export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.XLSX)
        
        # Create a new job instance
        export_pdf_job = ExportPDFJob(
            input_asset=input_asset, 
            export_pdf_params=export_pdf_params
        )
        
        # Submit the job and get the result
        location = pdf_services.submit(export_pdf_job)
        pdf_services_response = pdf_services.get_job_result(location, ExportPDFResult)
        
        # Get content from the resulting asset
        result_asset = pdf_services_response.get_result().get_asset()
        stream_asset = pdf_services.get_content(result_asset)
        
        # Save the result to Excel file
        with open(excel_path, "wb") as file:
            file.write(stream_asset.get_input_stream())
            
        logger.info(f"Successfully converted PDF to Excel: {excel_path}")
        return True
        
    except (ServiceApiException, ServiceUsageException, SdkException) as e:
        logger.error(f"Adobe API error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in PDF to Excel conversion: {e}")
        return False