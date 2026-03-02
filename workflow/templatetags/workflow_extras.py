from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_diff(workflow_instance):
    """
    Compares the target (request) with the original employee record.
    Returns HTML with highlighted changes.
    """
    target = workflow_instance.target  # This is the ProfileUpdateRequest
    employee = target.employee         # This is the original Employee record
    
    fields_to_compare = {
        'phone_number': 'Phone',
        'address': 'Address',
    }
    
    diff_html = '<ul class="list-unstyled mb-0">'
    
    for field, label in fields_to_compare.items():
        old_val = getattr(employee, field)
        new_val = getattr(target, field)
        
        if str(old_val) != str(new_val):
            diff_html += f'''
                <li class="text-xs">
                    <span class="text-secondary">{label}:</span> 
                    <del class="text-danger">{old_val}</del> 
                    <i class="bi bi-arrow-right mx-1"></i>
                    <ins class="text-success fw-bold">{new_val}</ins>
                </li>'''
    
    # Handle Skills Difference from proposed_data
    if hasattr(target, 'proposed_data') and isinstance(target.proposed_data, dict):
        for key, new_level in target.proposed_data.items():
            try:
                skill_id = int(key)
                # Find the existing level for this skill
                existing_skill = employee.skill_profiles.filter(skill_id=skill_id).first()
                old_level = existing_skill.level if existing_skill else 0
                
                if old_level != new_level:
                    skill_name = existing_skill.skill.name if existing_skill else f"Skill #{skill_id}"
                    diff_html += f'''
                        <li class="text-xs">
                            <span class="text-secondary">{skill_name}:</span> 
                            <span class="badge bg-light text-dark">{old_level}</span> 
                            <i class="bi bi-arrow-right mx-1"></i>
                            <span class="badge bg-success">{new_level}</span>
                        </li>'''
            except (ValueError, TypeError):
                # This is a PII field or other metadata, skip in skill processing
                continue

    diff_html += '</ul>'
    return mark_safe(diff_html)

@register.filter
def get_doc_diff(doc):
    """
    Compares the original_content with the current content for an InternalDocument.
    Returns a clean HTML representation of additions and deletions.
    """
    import difflib
    from django.utils.html import strip_tags
    
    # Check if doc has the required fields
    if not hasattr(doc, 'original_content') or not doc.original_content:
        return mark_safe("<p class='text-muted'>No original content found for comparison.</p>")
    
    # We strip tags for a cleaner text-based diff
    old_lines = strip_tags(doc.original_content).splitlines()
    new_lines = strip_tags(doc.content).splitlines()
    
    diff = difflib.HtmlDiff().make_table(old_lines, new_lines, context=True, numlines=3)
    
    custom_style = """
    <style>
        .diff_table { width: 100%; font-size: 0.85rem; border-collapse: collapse; }
        .diff_header { background: #f8f9fa; }
        .diff_next { display: none; }
        .diff_add { background-color: #e6ffec; text-decoration: none; border-left: 3px solid #00a67d; }
        .diff_chg { background-color: #f1f5f9; }
        .diff_sub { background-color: #ffebe9; text-decoration: line-through; border-left: 3px solid #cf222e; }
    </style>
    """
    return mark_safe(custom_style + diff)

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary.
    """
    if not dictionary:
        return None
    return dictionary.get(key)