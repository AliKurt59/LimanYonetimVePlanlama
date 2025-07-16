import re

def parse_container_type(c_type_str):
    """
    Verilen konteyner tipi string'ini (örn: "40 REEFER") analiz eder
    ve boyutunu (int) ile reefer olup olmadığını (bool) döndürür.
    """
    if not c_type_str: 
        return 0, None
    
    size_match = re.match(r"(\d+)", c_type_str)
    size = int(size_match.group(1)) if size_match else 0
    is_reefer = "REEFER" in c_type_str.upper()
    
    return size, is_reefer