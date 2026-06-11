import requests
import xml.etree.ElementTree as ET
from typing import Generator, Dict, Any, List, Optional

class OAIError(Exception):
    """Exception raised for OAI-PMH protocol errors."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"OAI-PMH Error ({code}): {message}")

class OAIClient:
    """A client library for fetching metadata from OAI-PMH repositories.
    
    Default base URL is configured for the Vernadsky National Library of Ukraine (NBUV) DSpace repository:
    https://dspace.nbuv.gov.ua/oai/request
    """
    
    DEFAULT_BASE_URL = "https://dspace.nbuv.gov.ua/oai/request"
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url
        self.ns = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

    def _request(self, verb: str, **params) -> ET.Element:
        """Helper to make HTTP request to OAI-PMH endpoint and parse XML."""
        payload = {'verb': verb, **params}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Follow redirects (-L equivalent in requests) is default in requests.get
        response = requests.get(self.base_url, params=payload, headers=headers)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Check for OAI-PMH errors
        error_el = root.find('oai:error', self.ns)
        if error_el is not None:
            code = error_el.attrib.get('code', 'unknown')
            message = error_el.text or ''
            raise OAIError(code, message.strip())
            
        return root

    def identify(self) -> Dict[str, Any]:
        """Returns repository identification info."""
        root = self._request('Identify')
        identify_el = root.find('oai:Identify', self.ns)
        if identify_el is None:
            raise ValueError("Invalid OAI-PMH response: Identify section missing")
            
        data = {}
        for child in identify_el:
            tag_name = child.tag.split('}')[-1]
            if tag_name == 'description':
                # description can contain oai-identifier details
                oai_id_el = child.find('.//{http://www.openarchives.org/OAI/2.0/oai-identifier}oai-identifier')
                if oai_id_el is None:
                    # fallback in case of missing namespaces inside description
                    oai_id_el = child.find('.//{*}oai-identifier')
                if oai_id_el is not None:
                    oai_id_data = {}
                    for id_child in oai_id_el:
                        id_tag = id_child.tag.split('}')[-1]
                        oai_id_data[id_tag] = id_child.text.strip() if id_child.text else ''
                    data['oai_identifier'] = oai_id_data
            else:
                data[tag_name] = child.text.strip() if child.text else ''
        return data

    def list_sets(self) -> Generator[Dict[str, str], None, None]:
        """Yields all sets (collections) in the repository."""
        resumption_token = None
        while True:
            if resumption_token:
                root = self._request('ListSets', resumptionToken=resumption_token)
            else:
                root = self._request('ListSets')
                
            list_sets_el = root.find('oai:ListSets', self.ns)
            if list_sets_el is None:
                break
                
            for set_el in list_sets_el.findall('oai:set', self.ns):
                spec = set_el.find('oai:setSpec', self.ns)
                name = set_el.find('oai:setName', self.ns)
                yield {
                    'setSpec': spec.text.strip() if spec is not None and spec.text else '',
                    'setName': name.text.strip() if name is not None and name.text else ''
                }
                
            resumption_token_el = list_sets_el.find('oai:resumptionToken', self.ns)
            if resumption_token_el is not None and resumption_token_el.text:
                resumption_token = resumption_token_el.text.strip()
            else:
                break

    def list_metadata_formats(self, identifier: Optional[str] = None) -> List[Dict[str, str]]:
        """Returns metadata formats supported by the repository or for a specific item."""
        params = {}
        if identifier:
            params['identifier'] = identifier
            
        root = self._request('ListMetadataFormats', **params)
        formats_el = root.find('oai:ListMetadataFormats', self.ns)
        if formats_el is None:
            return []
            
        formats = []
        for fmt_el in formats_el.findall('oai:metadataFormat', self.ns):
            prefix = fmt_el.find('oai:metadataPrefix', self.ns)
            schema = fmt_el.find('oai:schema', self.ns)
            ns = fmt_el.find('oai:metadataNamespace', self.ns)
            formats.append({
                'metadataPrefix': prefix.text.strip() if prefix is not None and prefix.text else '',
                'schema': schema.text.strip() if schema is not None and schema.text else '',
                'metadataNamespace': ns.text.strip() if ns is not None and ns.text else ''
            })
        return formats

    def list_records(self, metadata_prefix: str = "oai_dc", set_spec: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """Yields records from the repository. Handles pagination automatically."""
        params = {'metadataPrefix': metadata_prefix}
        if set_spec:
            params['set'] = set_spec
            
        resumption_token = None
        
        while True:
            if resumption_token:
                root = self._request('ListRecords', resumptionToken=resumption_token)
            else:
                root = self._request('ListRecords', **params)
                
            list_records_el = root.find('oai:ListRecords', self.ns)
            if list_records_el is None:
                break
                
            for record_el in list_records_el.findall('oai:record', self.ns):
                yield self._parse_record(record_el)
                
            resumption_token_el = list_records_el.find('oai:resumptionToken', self.ns)
            if resumption_token_el is not None and resumption_token_el.text:
                resumption_token = resumption_token_el.text.strip()
            else:
                break

    def get_record(self, identifier: str, metadata_prefix: str = "oai_dc") -> Dict[str, Any]:
        """Gets a single record by its identifier."""
        root = self._request('GetRecord', identifier=identifier, metadataPrefix=metadata_prefix)
        get_record_el = root.find('oai:GetRecord', self.ns)
        if get_record_el is None:
            raise ValueError(f"Record {identifier} not found in response")
            
        record_el = get_record_el.find('oai:record', self.ns)
        if record_el is None:
            raise ValueError(f"Record {identifier} not found in response")
            
        return self._parse_record(record_el)

    def _parse_record(self, record_el: ET.Element) -> Dict[str, Any]:
        """Internal helper to parse an XML record into a Python dict."""
        header_el = record_el.find('oai:header', self.ns)
        metadata_el = record_el.find('oai:metadata', self.ns)
        
        record_data = {
            'header': {},
            'metadata': None
        }
        
        if header_el is not None:
            status = header_el.attrib.get('status')
            identifier = header_el.find('oai:identifier', self.ns)
            datestamp = header_el.find('oai:datestamp', self.ns)
            
            record_data['header'] = {
                'identifier': identifier.text.strip() if identifier is not None and identifier.text else '',
                'datestamp': datestamp.text.strip() if datestamp is not None and datestamp.text else '',
                'status': status,
                'set_specs': [s.text.strip() for s in header_el.findall('oai:setSpec', self.ns) if s.text]
            }
            
        if metadata_el is not None:
            dc_el = metadata_el.find('oai_dc:dc', self.ns)
            if dc_el is not None:
                metadata = {}
                for child in dc_el:
                    tag_name = child.tag.split('}')[-1]
                    if tag_name not in metadata:
                        metadata[tag_name] = []
                    metadata[tag_name].append(child.text.strip() if child.text else '')
                record_data['metadata'] = metadata
                
        return record_data
