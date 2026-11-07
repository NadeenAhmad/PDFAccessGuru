from typing import Any, Optional
import re
from pikepdf import Array, Dictionary, Integer, Object, Pdf

from pdfaccessguru.exceptions.mapping_exceptions.step_function_traversal_exception import StepFunctionTraversalException


# Strip "(... )" or "{...}" decorations from a single path segment.
_DECORATION_RE = re.compile(r"\s*[({].*$")

# A clean segment looks like "pages" or "pages[0]".
_SEGMENT_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)(?:\[(\d+)\])?$")


def _resolve_context(context: str, pdf: Pdf) -> Object | Pdf:
    """
    Walk a veraPDF context path through pikepdf, return the target object.

    Raises:
    - exception {@link StepFunctionTraversalException} if
        the step function has a bug and cannot handle a path segment, index or current pikepdf
        object during traversal.
    """
    if not context:
        raise StepFunctionTraversalException("NULL CONTEXT")
    current: Any = pdf

    for name, idx in _parse_segments(context):
        try:
            current = _step(current, name, idx)
        except (KeyError, IndexError, AttributeError):
            raise StepFunctionTraversalException(name)

        if current is None:
            raise StepFunctionTraversalException(name)
    return current

def resolve_context_parent_element(context: str, pdf: Pdf) -> Object:
    """
    Resolve the parent element of the by context resolved element.

    Raises:
    - ValueError: if the context path resolves to less than 2 elements.
    - exception {@link StepFunctionTraversalException} if resolve_all_elements_on_context fails.
    """
    elements = resolve_all_elements_on_context(context, pdf)
    if len(elements) < 2:
        raise ValueError(f"Context path '{context}' resolves to less than 2 elements.")
    return elements[-2]

def resolve_all_elements_on_context(context: str, pdf: Pdf) -> list[Object]:
    """
    Walk a veraPDF context path through pikepdf, 
    return all pdf elements found on the path as list of pikepdf.Object's 
    in the order of the context path.

    Used in affected_element_detector's, e.g. to resolve the parent element of the affected element.
    Internally also uses the step function to traverse the context path.

    Arguments:
        - context: the context path to resolve, should not be empty.
        - pdf: the pikepdf.Pdf object to resolve the context path on

    Returns:
        - list of all pdf elements (type pikepdf.Object) found on the path, 
        is empty if resolving context results in element "None" or if the context is empty 
        or if the context results in the whole pdf.

    Raises:
    - exception {@link StepFunctionTraversalException} if
        the step function has a bug and cannot handle a path segment, index or current pikepdf
        object during traversal.
    """
    if not context:
        return []

    elements: list[Object] = []
    current: Any = pdf

    for name, idx in _parse_segments(context):
        try:
            current = _step(current, name, idx)
            if current is None :
                return elements
            if isinstance(current, Object) :
                elements.append(current)
        except (KeyError, IndexError, AttributeError):
            raise StepFunctionTraversalException(name)
        
    return elements


def _parse_segments(context: str):
    """Yield clean (name, index) tuples from a veraPDF context path."""
    for raw in _split_context_path(context):
        cleaned = _DECORATION_RE.sub("", raw).strip()
        if not cleaned:
            continue
        m = _SEGMENT_RE.match(cleaned)
        if not m:
            yield cleaned, 0
            continue
        yield m.group(1), int(m.group(2)) if m.group(2) else 0


def _split_context_path(context: str) -> list[str]:
    """
    Split context path by '/' while ignoring slashes inside veraPDF decorations
    like '(...)' or '{...}'.

    Use this instead of str.split("/") to avoid breaking segments that contain slashes, such as
    "Properties[6](http://purl.org/dc/elements/1.1/ - dc:title)".
    """
    parts: list[str] = []
    buf: list[str] = []
    paren_depth = 0
    brace_depth = 0

    for ch in context:
        if ch == "/" and paren_depth == 0 and brace_depth == 0:
            parts.append("".join(buf))
            buf = []
            continue

        buf.append(ch)

        if ch == "(":
            paren_depth += 1
        elif ch == ")" and paren_depth > 0:
            paren_depth -= 1
        elif ch == "{":
            brace_depth += 1
        elif ch == "}" and brace_depth > 0:
            brace_depth -= 1

    parts.append("".join(buf))
    return parts


def _step(current: Any, name: str, index: int) -> Optional[Any]:
    """
    One step of the walk. Given the current pikepdf object and the next
    path segment, return the next object - or None if we don't know how
    to follow that segment yet. Extend this as new segments come up.

    If parameter current is directly returned we stay
    on the current element, possible the whole pdf.
    """
    resolver = RESOLVERS.get(name)

    if resolver is None:
        raise StepFunctionTraversalException(name)
        

    return resolver(current, index)


# die einzelnen handler....

def handle_root(current, index):
    return current


def handle_catalog(current, index):
    return current.Root if isinstance(current, Pdf) else current


def handle_lang(current,index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.get("/Lang")
    return None

def handle_names(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.get("/Names")
    return None


def handle_embeddedFiles(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.Names.EmbeddedFiles
    return None


def handle_OCProperties(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.get("/OCProperties")
    return None


def handle_DefaultConfig(current, index):
    if isinstance(current, Dictionary):
        return current.get("/D")
    return None

# acroForm is the root element for interactive elements
def handle_AcroForm(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.get("/AcroForm")
    return None

# Fields Array (list of all form fields)
def handle_Fields(current, index):
     # Fields Array (list of all form fields)
    if isinstance(current, Dictionary):
        fields = current.get("/Fields")
        if fields is None:
            return None
        if isinstance(fields, Array):
            return fields[index] if 0 <= index < len(fields) else None
        return fields if index == 0 else None
    return None

# MarkInfo is a dictionary in the catalogue containing accessibility flags
        # Typically contains /Marked (boolean) and /UserProperties (boolean)
def handle_MarkInfo(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.get("/MarkInfo")
    return None

# Outlines root dictionary lives in the catalog
def handle_Outlines(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.get("/Outlines")
    return None

# Return the raw page Dictionary (not the pikepdf.Page wrapper)
# so downstream isinstance(element, Dictionary) checks work.
def handle_Pages(current, index):
    if isinstance(current, Pdf):
        return current.pages[index].obj

    if isinstance(current, Dictionary):
        kids = current.get("/Kids")
        if isinstance(kids, Array) and index < len(kids):
            return kids[index]

    return None


def handle_Annots(current, index):
    if not isinstance(current, Dictionary):
        return None
    annots = current.get("/Annots")
    if isinstance(annots, Array) and index < len(annots):
        return annots[index]
    return None


def handle_A(current, index):
    if not isinstance(current, Dictionary):
        return None
    
    action = current.get("/A")
    if action is None:
        return None
    if index == 0:          #veraPDF nutzt [0], obwohl es kein Array ist
        return action
    return None

#man kommt von /A zu /C über /A, /R,/C 
def handle_C (current, index):
    media_clip = current.get("/C") if isinstance (current, Dictionary) else None
    if media_clip is not None and index == 0:
        return media_clip
    
    rendition = current.get("/R") if isinstance (current, Dictionary) else None
    if rendition is None:
        return None
    media_clip = rendition.get("/C") if isinstance(current, Dictionary) else None
    if media_clip is not None and index == 0:
        return media_clip
    
    return None


    
    
    
def handle_Metadata(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    if isinstance(holder, Dictionary):
        return holder.get("/Metadata")
    return None


def handle_XMPPackage(current, index):
    return current

def handle_Properties(current, index):
    return current


def handle_StructTreeRoot(current, index):
    holder = current.Root if isinstance(current, Pdf) else current
    return holder.get("/StructTreeRoot")


def handle_Kids(current, index):
    kids = current.get("/K") if hasattr(current, "get") else None

    if kids is None:
        return None

    if isinstance(kids, Array):
        for i in range(index, len(kids)):
            kid = kids[i]
            if not isinstance(kid, int):
                return kid
        return None

    return kids if index == 0 else None
        

    


def handle_ContentStream(current, index):
    return current


def handle_Gylphs(current, index):
    return current


def handle_Encoding(current, index):
    encoding = current.get("/Encoding") if hasattr(current, 'get') else None
    if encoding is None:
        return None
    if isinstance(encoding, Array) and index < len(encoding):
        return encoding[index]
    return encoding
        


def handle_UseCMap(current, index):
    use_cmap = current.get("/UseCMap") if hasattr(current, 'get') else None
    if use_cmap is None:
        return None
    if isinstance(use_cmap, Array) and index < len(use_cmap):
        return use_cmap[index]
    return use_cmap


# FontDescriptor lives in font dictioary
def handle_FontDescriptor(current, index):  
    if isinstance(current, Dictionary):
        return current.get("/FontDescriptor")
    return None

def handle_DescendantFonts(current, index):
    descendantFont = current.get("/DescendantFonts") if hasattr(current, 'get') else None
    if descendantFont is None:
        return None
    if isinstance (descendantFont, Array) and index < len(descendantFont):
        return descendantFont[index]
    return descendantFont


### Reihenfolge ist bei list(fonts.keys()) nicht gegeben
def handle_Font(current, index):
    if isinstance(current, Dictionary) and "/Resources" in current:
        fonts = current["/Resources"].get("/Font")
        if fonts:
            keys = list(fonts.keys())
            if 0 <= index < len(keys):
                return fonts[keys[index]]
    return None


def handle_XObject(current, index):
    if isinstance(current, Dictionary) and "/Resources" in current:
        xObject = current["/Resources"].get("/XObject")
        if xObject is None:
            return None
        if isinstance(xObject, Dictionary):
            keys = list (xObject.keys())
            if 0 <= index < len(keys):
                return xObject[keys[index]]
            return None
        if isinstance(xObject, Array):
            return xObject[index] if index < len(xObject) else None
    return None

def handle_PDFUAIdentification(current, index):
    """
    Implementation date: 08.06.2026 23:05
    """
    return current

def handle_trailer(current, index):
    """
    Implementation date: 08.06.2026 23:30
    """
    if isinstance(current, Pdf):
        return current.trailer
    return None

def handle_encrypt(current, index):
    if isinstance(current, Dictionary):
        return current.get("/Encrypt")
    return None

RESOLVERS = {
    # root
    "root": handle_root,
    "document": handle_root,
    "PDDocument": handle_root,

    # catalog
    "catalog": handle_catalog,
    "PDCatalog": handle_catalog,

    # lang
    "Lang": handle_lang,
    "lang": handle_lang,

    # names
    "Names": handle_names,
    "names": handle_names,

    # embedded files
    "EmbeddedFiles": handle_embeddedFiles,
    "embeddedfiles": handle_embeddedFiles,

    # OCProperties
    "OCProperties": handle_OCProperties,
    "PDOCProperties": handle_OCProperties,

    # DefaultConfig
    "D": handle_DefaultConfig,
    "DefaultConfig": handle_DefaultConfig,

    # AcroForm
    "AcroForm": handle_AcroForm,
    "acroform": handle_AcroForm,

    # Fields
    "Fields": handle_Fields,
    "fields": handle_Fields,
    "FormFields": handle_Fields,
    "formFields": handle_Fields,

    # MarkInfo
    "MarkInfo": handle_MarkInfo,
    "markInfo": handle_MarkInfo,

    # Outlines
    "outlines": handle_Outlines,
    "Outlines": handle_Outlines,

    # Pages
    "pages": handle_Pages,
    "PDPage": handle_Pages,

    # Annots
    "annots": handle_Annots,
    "PDAnnot": handle_Annots,
    
    # A (Action Dictionary)
    "A": handle_A,
    
    # C (Media Clip Data Dictionary)
    "C": handle_C,

    # Metadata
    "metadata": handle_Metadata,
    "Metadata": handle_Metadata,
    "PDMetadata": handle_Metadata,

    # XMP
    "XMPPackage": handle_XMPPackage,

    # Properties
    "Properties": handle_Properties,
    "properties": handle_Properties,

    # StructTree
    "StructTreeRoot": handle_StructTreeRoot,
    "structTreeRoot": handle_StructTreeRoot,

    # Kids
    "K": handle_Kids,
    "children": handle_Kids,

    # ContentStream
    "contentStream": handle_ContentStream,
    "operators": handle_ContentStream,
    "content": handle_ContentStream,
    "contentItem": handle_ContentStream,

    # Glyphs
    "usedGlyphs": handle_Gylphs,
    "UsedGlyphs": handle_Gylphs,
    "used_glyphs": handle_Gylphs,

    # FontDescriptor
    "fontDescriptor": handle_FontDescriptor,
    "FontDescriptor": handle_FontDescriptor,
    "PDFontDescriptor": handle_FontDescriptor,

    # Encoding
    "Encoding": handle_Encoding,
    "encoding": handle_Encoding,

    # CMap
    "UseCMap": handle_UseCMap,
    "useCMap": handle_UseCMap,

    # DescendantFonts
    "DescendantFonts": handle_DescendantFonts,
    "descendantFonts": handle_DescendantFonts,

    # Font
    "font": handle_Font,
    "PDFont": handle_Font,

    # XObject
    "XObject": handle_XObject,
    "xobject": handle_XObject,
    "xObject": handle_XObject,

    # PDFUAIdentification
    "PDFUAIdentification": handle_PDFUAIdentification,

    # trailer
    "trailer": handle_trailer,
    # Encrypt
    "Encrypt": handle_encrypt,
}