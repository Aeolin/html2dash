import sys
import uuid
import xml.etree.ElementTree as xml
import os
import re
from lastitemiterator import lii
from pathlib import Path
from stringbuilder import StringBuilder
import hashlib

BUF_SIZE = 65536
ATTRIBUTE_TRANSLATIONS = {'class': 'className'}
TYPE_CONVERSIONS = {'str': str, 'int': int, 'float': float, 'bool': bool}
CONFIG_TYPE_GETTER = {'str': 'get', 'int': 'getint', 'float': 'getfloat', 'bool': 'getboolean'}
LIB_CALLS = {'date': 'date', 'time': 'time', 'timedelta': 'timedelta', 'datetime': 'datetime', 'pd': 'pd', 'px': 'px', 'req': 'req', 'json': 'jp', 'format': 'fmt', 'io': 'io'}
config = None
file_name = None


def convert(path, directory, p_config, use_pages=False, page_name=None):
    with open(path, "rb") as html:
        filehash = hashlib.md5()
        while True:
            data = html.read(BUF_SIZE)
            if not data:
                break
            filehash.update(data)

        hash = filehash.hexdigest()
        name = Path(path).stem.replace(" ", "_")
        out_name = f"./{directory}/html2dash_generated_{name}_{hash}.py"
        if os.path.exists(out_name):
            return Path(out_name).stem

        for file in os.listdir(directory):
            if os.path.isfile(Path(directory, file)) and file.startswith(f"html2dash_generated_{name}_"):
                os.remove(Path(directory, file))

        sys.modules[__name__].config = p_config
        sys.modules[__name__].file_name = name.lower()
        html.seek(0)
        tree = xml.parse(html)
        root = tree.getroot()
        reformat_ids(root)
        layout_builder = StringBuilder()
        generate_layout_code(root, layout_builder)
        transform_builder = StringBuilder()
        generate_transforms(root, transform_builder)
        update_builder = StringBuilder()
        generate_update_code_new(root, update_builder, use_pages)
        with open(f"./templates/{'paged_' if use_pages else ''}template.pyt", "r") as template:
            template = template.read().format(page=(page_name or "/" + re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()), methods=str(transform_builder), layout=str(layout_builder), update=str(update_builder))

        with open(out_name, "w", encoding="utf-8") as output:
            output.write(template)
            return Path(out_name).stem


def reformat_ids(node):
    for child in node:
        id = child.get("id")
        if id is not None:
            child.set("id", f"{file_name}_{id}")

        if child.tag == "{d2h}parameter":
            input = child.get("input")
            if input is not None:
                child.set("input", f"{file_name}_{input}")

        reformat_ids(child)


def format_value(value):
    if value is None:
        return None
    elif value.startswith('"') and value.endswith('"'):
        return value
    elif value == "None":
        return "None"
    elif value == "True":
        return "True"
    elif value == "False":
        return "False"
    elif value == "[]":
        return []
    elif value == "{}":
        return {}
    elif re.match("^\\d+$", value):
        return int(value)
    elif re.match("^\\d+\\.\\d+$", value):
        return float(value)
    elif re.match("^\\D.*\\(([^\\)]*)\\)$", value):
        return value
    else:
        return f'"{value}"'


def generate_df_function(node, builder):
    if node.tag == "{df}select":
        builder.append("df[")
        generate_function_call(node[0], builder, True)
        builder.append("]")
    else:
        generate_lib_call(node, builder, "df")


def generate_transforms(node, builder):
    transforms = node.findall(".//pd:transform", namespaces={"pd": "pd"})
    for last, transform in lii(transforms):
        name = transform.get("method_name")
        if name is None:
            name = f"transform_generated_{uuid.uuid4().hex}"
            transform.set("method_name", name)

        builder.append_line(f"def {name}(df):")
        builder.push_indent()
        for child in transform:
            if child.tag.startswith("{df}"):
                in_place = bool(child.get("inplace") or False)
                if not in_place:
                    builder.append("df = ")
                generate_df_function(child, builder)
                builder.append_line()

        builder.append("return df")
        builder.pop_indent()
        if not last:
            builder.append_line(builder.line_break)


def generate_function_call(node, builder, suppress_linebreak=False):
    builder.push_indent()
    if node.tag == "{pd}transform":
        if not suppress_linebreak and config.getboolean("dash2html", "ProduceDebuggableCode"):
            builder.append_line()
        generate_transform(node, builder)
    elif node.tag == "{d2h}field":
        builder.append(f"model.{node.text}")
    elif node.tag == "{d2h}method":
        generate_method(node, builder)
    elif node.tag == "{d2h}parameter":
        generate_parameter(node, builder)
    elif node.tag == "{d2h}dict":
        generate_dict(node, builder)
    elif node.tag == "{d2h}config":
        generate_config(node, builder)
    elif node.tag == "{d2h}list":
        generate_list(node, builder)
    else:
        if not suppress_linebreak and config.getboolean("dash2html", "ProduceDebuggableCode"):
            builder.append_line()
        generate_lib_call(node, builder, None)
    builder.pop_indent()


def generate_list(node, builder):
    param_name = node.get("name")
    if param_name is not None:
        builder.append(f"{param_name}=")

    items = node.get("items")
    builder.append("[")
    if items is not None:
        builder.append(", ".join([format_value(x.strip()) for x in items.split(",")]))
        if len(node) > 0:
            builder.append(", ")

    generate_parameter_list(node, builder, suppress_linebreak=True)
    builder.append("]")


def generate_transform(node, builder):
    name = node.get("method_name")
    data = node.find("{pd}transform.data")
    if data is None:
        return None

    builder.append(f"{name}(")
    generate_function_call(data[0], builder)
    builder.append(")")


def generate_lib_call(node, builder, lib_prefix=None):
    match = re.match("^(?:{(.*)})?(.*)$", node.tag)
    namespace = match.group(1)
    tag = match.group(2)
    suppress_new = node.get("__suppress_new__")
    if suppress_new is None:
        suppress_new = "False"

    if tag == 'new' and suppress_new == "False":
        tag = None

    if lib_prefix is None:
        if namespace in LIB_CALLS:
            lib_prefix = LIB_CALLS[namespace]
        else:
            return

    name = node.get("name")
    if name is not None:
        builder.append(f"{name}=")

    builder.append(f"{lib_prefix}{'.' if tag is not None else ''}{tag or ''}(")
    attrib_childs = filter(lambda x: x.tag.startswith(f"{node.tag}."), node)
    childs = filter(lambda x: not x.tag.startswith(f"{node.tag}."), node)

    generate_parameter_list(childs, builder, len(node.attrib) > 0)
    for last, attrib_child in lii(attrib_childs):
        attrib_name = attrib_child.tag.replace(f"{node.tag}.", "")
        builder.append(f"{attrib_name}=")
        generate_function_call(attrib_child[0], builder)
        if not last or len(node.attrib) > 0:
            builder.append(", ")

    for last, attr in lii(node.attrib):
        if attr == "name" or attr == "__suppress_new__":
            continue
        builder.append(f"{attr}={format_value(node.attrib[attr])}")
        if not last:
            builder.append(", ")
    builder.append(")")


def generate_dict(node, builder):
    param_name = node.get("name")
    if param_name is not None:
        builder.append(f"{param_name}=")

    builder.append("dict(")
    for last, child in lii(node):
        if len(child) > 0:
            builder.append(f"{child.tag}={generate_function_call(child)}")
        else:
            builder.append(f"{child.tag}={format_value(child.text)}")
        if not last:
            builder.append(", ")
    builder.append(")")


def generate_method(method, builder, from_model=True):
    method_name = method.get("method_name")
    param_name = method.get("name")
    if param_name is not None:
        builder.append(f"{param_name}=")

    builder.append(f"{'model.' if from_model else ''}{method_name}(")
    generate_parameter_list(method, builder)
    builder.append(")")


def is_lib_call(node):
    match = re.match("^(?:{(.*)})?(.*)$", node.tag)
    namespace = match.group(1)
    tag = match.group(2)
    return namespace in LIB_CALLS or namespace == "df"


def generate_parameter_list(parameters, builder, trailing_comma=False, suppress_linebreak=False):
    for last, parameter in lii(parameters):
        generate_function_call(parameter, builder, suppress_linebreak)
        if not last or trailing_comma:
            if config.getboolean("dash2html", "ProduceDebuggableCode") and is_lib_call(parameter) and not suppress_linebreak:
                builder.append_line(", ")
            else:
                builder.append(", ")


def generate_parameter(parameter, builder):
    value = format_value(parameter.get("value") or parameter.text) or parameter.get('input')
    name = parameter.get("name")
    if name is not None:
        builder.append(f"{name}=")
    builder.append(value)


def generate_config(node, builder):
    key = node.get("key")
    type = node.get("type") or 'str'
    default = TYPE_CONVERSIONS[type](node.get("default"))
    key = ", ".join(key.split("."))
    builder.append(f"config.{CONFIG_TYPE_GETTER[type]}('{key}'")
    if default is not None:
        builder.append(f", fallback={default}")

    builder.append(")")


def generate_update_code_new(node, builder, use_pages):
    parent_map = {c: p for p in node.iter() for c in p}
    node_map = {n.get("id"): n for n in node.iter() if n.get("id") is not None}
    outputs = node.findall(".//dash:output", namespaces={"dash": "dash"})
    input_map = {n.get('id'): n for n in node.findall(".//dash:input", namespaces={"dash": "dash"})}
    output_groups = {}
    for output in outputs:
        parent = parent_map[output].get("id")
        if parent not in output_groups:
            output_groups[parent] = []

        output_groups[parent].append(output)

    if len(outputs) == 0 and len(input_map) == 0:
        return;

    for last_output, parent_id, outputs_in_parent in lii(output_groups.items()):
        inputs = node_map[parent_id].findall(".//d2h:parameter[@input]", namespaces={"d2h": "d2h"})
        builder.append_line(f"@{'' if use_pages else 'app.'}callback(")
        builder.push_indent()
        for last, output in lii(outputs_in_parent):
            builder.append(f'Output(component_id="{parent_id}", component_property="{output.get("component_property")}")')
            if not last or len(inputs) > 0:
                builder.append_line(",")

        for last, input in lii(inputs):
            input_node = input_map[input.get("input")]
            input_parent_id = parent_map[input_node].get("id")
            builder.append(f'Input(component_id="{input_parent_id}", component_property="{input_node.get("component_property")}")')
            if not last:
                builder.append_line(",")

        builder.append_line(")")
        builder.pop_indent()
        builder.append(f"def update_{parent_id}(")
        for last, input in lii(inputs):
            input_node = input_map[input.get("input")]
            builder.append(input_node.get("id"))
            if not last:
                builder.append(", ")

        builder.append_line("):")
        builder.push_indent()

        for output in outputs_in_parent:
            value = output.get("value")
            property = output.get("component_property")
            builder.append(f"__output_{parent_id}_{property} = ")

            if value is not None:
                builder.append(format_value(value))
            elif len(output) > 0:
                generate_function_call(output[0], builder, True)
            else:
                builder.append("None")

            builder.append_line()

        builder.append("return ")
        for last, output in lii(outputs_in_parent):
            property = output.get("component_property")
            builder.append(f"__output_{parent_id}_{property}")
            if not last:
                builder.append(", ")

        builder.pop_indent()

        if not last_output:
            builder.append_line(builder.line_break)



def generate_update_code(node, builder, use_pages):
    parent_map = {c: p for p in node.iter() for c in p}
    outputs = node.findall(".//dash:output", namespaces={"dash": "dash"})
    inputs = node.findall(".//dash:input", namespaces={"dash": "dash"})

    if len(outputs) == 0 and len(inputs) == 0:
        return;

    builder.append_line(f"@{'' if use_pages else 'app.'}callback(")
    builder.push_indent()
    for last, output in lii(outputs):
        id = parent_map[output].get("id")
        property = output.get("component_property")
        builder.append(f'Output(component_id="{id}", component_property="{property}")')
        if not last or len(inputs) > 0:
            builder.append_line(",")

    for last, input in lii(inputs):
        id = parent_map[input].get("id")
        property = input.get("component_property")
        builder.append(f'Input(component_id="{id}", component_property="{property}")')
        if not last:
            builder.append_line(",")

    builder.pop_indent()
    builder.append_line(")")
    builder.append("def update(")
    for last, input in lii(inputs):
        builder.append(input.get("id"))
        if not last:
            builder.append(", ")

    builder.append_line("):")
    builder.push_indent()
    for last, output in lii(outputs):
        id = parent_map[output].get("id")
        property = output.get("component_property")
        value = output.get("value")
        builder.append(f"__output_{id}_{property} = ")
        if value is not None:
            builder.append(format_value(value))
        elif len(output) > 0:
            generate_function_call(output[0], builder, True)
        else:
            builder.append("None")

        if not last:
            builder.append_line()

    builder.append_line()
    builder.append('return ')
    for last, output in lii(outputs):
        id = parent_map[output].get("id")
        property = output.get("component_property")
        builder.append(f'__output_{id}_{property}')
        if not last:
            builder.append(", ")


def generate_layout_code(node, builder):
    match = re.match("^(?:{(.*)})?(.*)$", node.tag)
    tag = match.group(2)
    namespace = match.group(1) or "html"
    if namespace == "html":
        tag = tag.capitalize()

    builder.append(f"{namespace}.{tag}(")
    children = [x for x in node if not (x.tag.startswith(f"{tag}.") or x.tag.startswith(f"{node.tag}.") or x.tag.startswith("{d2h}") or x.tag.startswith("{dash}"))]
    nested_attributes = [x for x in node if x.tag.startswith(f"{tag}.") or x.tag.startswith(f"{node.tag}.")]
    has_args = False
    if len(children) > 0:
        builder.append_line("[")
        builder.push_indent()
        for last, child in lii(children):
            generate_layout_code(child, builder)
            if not last:
                builder.append_line(",")
                builder.append_line()
        builder.pop_indent()
        builder.append("]")
        has_args = True
    elif len(node) == 0:
        if node.text is not None and node.text != "":
            if '\n' in node.text or '\r' in node.text:
                builder.append_line(f'"""{node.text}"""')
            else:
                builder.append(f'"{node.text}"')
            has_args = True

    builder.push_indent()
    if len(node.attrib) > 0 and has_args:
        builder.append_line(",")

    for last_attrib, key, value in lii(node.attrib.items()):
        if key in ATTRIBUTE_TRANSLATIONS:
            key = ATTRIBUTE_TRANSLATIONS[key]

        if key == "style":
            builder.append("style={")
            for last_item, item in lii(value.split(";")):
                key, value = item.split(":")
                builder.append(f'"{key.strip()}": "{value.strip()}"{"" if last_item else ","}')
            builder.append(f"}}{'' if last_attrib else ','}")
        else:
            builder.append(f"{key}={format_value(value)}")

        if not last_attrib:
            builder.append_line(", ")

    if len(nested_attributes) > 0 and (has_args or len(node.attrib) > 0):
        builder.append_line(",")

    for last, child in lii(nested_attributes):
        complex = bool(child.get("complex") or False)
        ctag = child.tag.split(".")[-1]
        if complex:
            builder.append(f"{ctag}=")
            generate_function_call(child[0], builder, False)
        else:
            builder.append(f"{ctag}={{")
            for last_item, item in lii(child):
                builder.append(f'"{item.tag}": {format_value(item.text.strip())}{"" if last_item else ","}')
            builder.append("}")
            if not last:
                builder.append_line(", ")
    builder.pop_indent()

    builder.append(")")
