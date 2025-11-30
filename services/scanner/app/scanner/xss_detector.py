from bs4 import BeautifulSoup, Comment
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class XSSContext:
    canary: str
    context_type: str # 'html_text', 'attribute_value', 'script_block', 'comment', 'url_param'
    tag_name: Optional[str] = None
    attribute_name: Optional[str] = None
    is_executable: bool = False
    evidence: str = ""

class XSSDetector:
    def generate_payloads(self, canary: str) -> List[str]:
        """
        Generates a small set of payloads centered on the canary.
        """
        return [
            canary, # Simple reflection check
            f"\"><script>alert('{canary}')</script>", # Break out of attribute/tag
            f"';alert('{canary}');//", # JS injection
            f"\" onmouseover=\"alert('{canary}')", # Attribute injection
            f"<img src=x onerror=alert('{canary}')>" # Tag injection
        ]

    def analyze_response(self, html_content: str, canary: str) -> List[XSSContext]:
        """
        Analyzes HTML content to find the canary and determine its context.
        """
        contexts = []
        if canary not in html_content:
            return contexts

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Search in text nodes
            for string in soup.find_all(string=True):
                if canary in string:
                    parent = string.parent
                    if parent.name == 'script':
                        # Inside script block
                        # Check if it's inside a string literal or raw code
                        # Simple heuristic: if it's in script, it's dangerous if not properly escaped
                        contexts.append(XSSContext(
                            canary=canary,
                            context_type='script_block',
                            tag_name='script',
                            is_executable=True, 
                            evidence=str(parent)[:200]
                        ))
                    elif isinstance(string, Comment):
                        contexts.append(XSSContext(
                            canary=canary,
                            context_type='comment',
                            is_executable=False,
                            evidence=str(string)
                        ))
                    else:
                        # Normal text
                        contexts.append(XSSContext(
                            canary=canary,
                            context_type='html_text',
                            tag_name=parent.name,
                            is_executable=False, 
                            evidence=str(parent)[:200]
                        ))

            # 2. Search in attributes
            for tag in soup.find_all(True): # All tags
                for attr_name, attr_value in tag.attrs.items():
                    # attr_value can be list (class) or string
                    values = attr_value if isinstance(attr_value, list) else [attr_value]
                    for val in values:
                        if canary in str(val):
                            is_exec = False
                            # Check for event handlers
                            if attr_name.lower().startswith('on'): 
                                is_exec = True
                            # Check for javascript: protocol
                            elif attr_name.lower() in ['href', 'src', 'action', 'data'] and ('javascript:' in str(val).lower()):
                                is_exec = True
                            # Check if payload broke out of attribute (e.g. found "> or " onmouseover=)
                            # This is hard to detect on the parsed tree because BS4 fixes it.
                            # But if we see a new attribute that wasn't there before... 
                            # Actually, if the injection worked, BS4 might parse it as a new attribute or tag.
                            # So we should also check if our payload created new tags/attributes.
                            # But for now, let's stick to simple context analysis.
                            
                            contexts.append(XSSContext(
                                canary=canary,
                                context_type='attribute_value',
                                tag_name=tag.name,
                                attribute_name=attr_name,
                                is_executable=is_exec,
                                evidence=f"<{tag.name} {attr_name}='{val}'>"
                            ))

        except Exception:
            # Fallback or ignore
            pass
            
        return contexts
