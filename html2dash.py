import sys
import uuid
import xml.etree.ElementTree as xml
import os
import re
from datetime import datetime

from lastitemiterator import lii
from pathlib import Path
from stringbuilder import StringBuilder
import hashlib
import json

VERSION = '0.3.5'
BUF_SIZE = 65536
ATTRIBUTE_TRANSLATIONS = {'class': 'className'}
TYPE_CONVERSIONS = {'str': str, 'int': int, 'float': float, 'bool': bool}
CONFIG_TYPE_GETTER = {'str': 'get', 'int': 'getint', 'float': 'getfloat', 'bool': 'getboolean'}
LIB_CALLS = {'date': 'date', 'time': 'time', 'timedelta': 'timedelta', 'datetime': 'datetime', 'pd': 'pd', 'px': 'px',
             'req': 'req', 'json': 'jp', 'format': 'fmt', 'io': 'io'}


class Html2Dash:

    def __init__(self, config, directory, use_pages):
        self.config = config
        self.directory = directory
        self.use_pages = use_pages
        page_file_path = Path(directory, "pages.json")
        if os.path.exists(page_file_path):
            with open(page_file_path, "r") as f:
                self.pages = json.load(f)
        else:
            self.pages = {}

    def save_page_file(self):
        with open(Path(self.directory, "pages.json"), "w") as f:
            json.dump(self.pages, f)

    def hash(self, file_stream):
        sha256 = hashlib.sha256()
        while True:
            data = file_stream.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)

        file_stream.seek(0)
        return sha256.hexdigest()

    def convert(self, path, page_name=None):
        with open(path, "rb") as html:
            html_hash = self.hash(html)
            name = Path(path).stem.replace(" ", "_")
            out_name = f"./{self.directory}/html2dash_generated_{name}.py"
            tree = xml.parse(html)
            root = tree.getroot()
            includes = self.find_includes(root, Path(path).parent)
            page_obj = self.pages.get(name, None)
            if page_obj is not None and page_obj["hash"] == html_hash and\
                    all([include[1]["hash"] == page_obj["includes"].get(include[0], None) for include in includes.items()]) and\
                    page_obj["html2dash_version"] == VERSION and\
                    os.path.exists(out_name):
                return
            elif page_obj is None:
                page_obj = {}
                self.pages[name] = page_obj

            page_obj["hash"] = html_hash
            page_obj["generated"] = datetime.utcnow().isoformat()
            page_obj["includes"] = {str(include): includes[include]["hash"] for include in includes}
            page_obj["html2dash_version"] = VERSION
            old_file = page_obj.get("generated_file", None)
            if old_file is not None and os.path.exists(out_name):
                os.remove(old_file)

            self.handle_includes(root, includes, Path(path).parent)
            self.reformat_ids(root, name)
            layout_builder = StringBuilder()
            self.generate_layout_code(root, layout_builder)
            transform_builder = StringBuilder()
            self.generate_transforms(root, transform_builder)
            update_builder = StringBuilder()
            self.generate_update_code_new(root, update_builder, self.use_pages)
            with open(f"./templates/{'paged_' if self.use_pages else ''}template.pyt", "r") as template:
                template = template.read().format(
                    page=(page_name or "/" + re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()),
                    methods=str(transform_builder), layout=str(layout_builder),
                    update=str(update_builder))

            with open(out_name, "w", encoding="utf-8") as output:
                output.write(template)
                page_obj["code_file"] = out_name
                self.save_page_file()
                return Path(out_name).stem

    def find_includes(self, node, path):
        nodes = node.findall(".//include")
        includes = {}
        for node in nodes:
            file = Path(path, node.get("src"))
            if os.path.exists(file):
                with open(file, "rb") as f:
                    fragment_hash = self.hash(f)
                    fragment_xml = xml.parse(f).getroot()
                    fragment_includes = self.find_includes(fragment_xml, file.parent)
                    includes[str(file)] = {"xml": fragment_xml, "hash": fragment_hash }
                    includes.update(fragment_includes)

        return includes

    def handle_includes(self, node, includes, path, index=0, parent=None):
        if parent is not None and node.tag == "include":
            src_path = Path(path, node.get("src"))
            src_name = str(src_path)
            if src_name in includes:
                fragment = includes[src_name]["xml"]
                self.handle_includes(fragment, includes, src_path.parent, 0, None)
                parent[index] = fragment

        for i in range(len(node)):
            self.handle_includes(node[i], includes, path, i, node)

    def reformat_ids(self, node, file_name):
        for child in node:
            id = child.get("id")
            if id is not None:
                child.set("id", f"{file_name}_{id}")

            if child.tag == "{d2h}parameter":
                input = child.get("input")
                if input is not None:
                    child.set("input", f"{file_name}_{input}")

                state = child.get("state")
                if state is not None:
                    child.set("state", f"{file_name}_{state}")

            self.reformat_ids(child, file_name)

    def format_value(self, value):
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
        elif re.match("^-?\\d+$", value):
            return int(value)
        elif re.match("^-?\\d+\\.\\d+$", value):
            return float(value)
        elif re.match("^\\D.*\\(([^\\)]*)\\)$", value):
            return value
        else:
            return f'"{value}"'

    def generate_df_function(self, node, builder):
        if node.tag == "{df}select":
            builder.append("df[")
            self.generate_function_call(node[0], builder, True)
            builder.append("]")
        elif node.tag == "{df}self":
            builder.append("df")
        else:
            self.generate_lib_call(node, builder, "df")

    def generate_transforms(self, node, builder):
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
                    self.generate_df_function(child, builder)
                    builder.append_line()

            builder.append("return df")
            builder.pop_indent()
            if not last:
                builder.append_line(builder.line_break)

    def generate_function_call(self, node, builder, suppress_linebreak=False):
        builder.push_indent()
        if node.tag == "{pd}transform":
            if not suppress_linebreak and self.config.getboolean("dash2html", "ProduceDebuggableCode"):
                builder.append_line()
            self.generate_transform(node, builder)
        elif node.tag == "{d2h}field":
            builder.append(f"model.{node.text}")
        elif node.tag == "{d2h}method":
            self.generate_method(node, builder)
        elif node.tag == "{d2h}parameter":
            self.generate_parameter(node, builder)
        elif node.tag == "{d2h}dict":
            self.generate_dict(node, builder)
        elif node.tag == "{d2h}config":
            self.generate_config(node, builder)
        elif node.tag == "{d2h}list":
            self.generate_list(node, builder)
        elif node.tag == "{d2h}not":
            self.generate_not(node, builder)
        else:
            if not suppress_linebreak and self.config.getboolean("dash2html", "ProduceDebuggableCode"):
                builder.append_line()
            self.generate_lib_call(node, builder, None)
        builder.pop_indent()

    def generate_not(self, node, builder):
        builder.append("not (")
        self.generate_function_call(node[0], builder)
        builder.append(")")

    def generate_list(self, node, builder):
        param_name = node.get("name")
        if param_name is not None:
            builder.append(f"{param_name}=")

        items = node.get("items")
        builder.append("[")
        if items is not None:
            builder.append(", ".join([self.format_value(x.strip()) for x in items.split(",")]))
            if len(node) > 0:
                builder.append(", ")

        self.generate_parameter_list(node, builder, suppress_linebreak=True)
        builder.append("]")

    def generate_transform(self, node, builder):
        name = node.get("method_name")
        data = node.find("{pd}transform.data")
        if data is None:
            return None

        builder.append(f"{name}(")
        self.generate_function_call(data[0], builder)
        builder.append(")")

    def generate_lib_call(self, node, builder, lib_prefix=None):
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

        self.generate_parameter_list(childs, builder, len(node.attrib) > 0)
        for last, attrib_child in lii(attrib_childs):
            attrib_name = attrib_child.tag.replace(f"{node.tag}.", "")
            builder.append(f"{attrib_name}=")
            self.generate_function_call(attrib_child[0], builder)
            if not last or len(node.attrib) > 0:
                builder.append(", ")

        for last, attr in lii(node.attrib):
            if attr == "name" or attr == "__suppress_new__":
                continue
            builder.append(f"{attr}={self.format_value(node.attrib[attr])}")
            if not last:
                builder.append(", ")
        builder.append(")")

    def generate_dict(self, node, builder):
        param_name = node.get("name")
        if param_name is not None:
            builder.append(f"{param_name}=")

        builder.append("dict(")
        for last, child in lii(node):
            if len(child) > 0:
                builder.append(f"{child.tag}={self.generate_function_call(child, builder)}, ")
            else:
                builder.append(f"{child.tag}={self.format_value(child.text)}")
            if not last or len(node.attrib) > (0 if param_name is None else 1):
                builder.append(", ")

        for last, attrib in lii(node.attrib):
            if attrib == "name":
                continue

            builder.append(f"{attrib}={self.format_value(node.attrib[attrib])}")
            if not last:
                builder.append(", ")

        builder.append(")")

    def generate_method(self, method, builder, from_model=True):
        method_name = method.get("method_name")
        param_name = method.get("name")
        if param_name is not None:
            builder.append(f"{param_name}=")

        builder.append(f"{'model.' if from_model else ''}{method_name}(")
        self.generate_parameter_list(method, builder)
        builder.append(")")

    def is_lib_call(self, node):
        match = re.match("^(?:{(.*)})?(.*)$", node.tag)
        namespace = match.group(1)
        tag = match.group(2)
        return namespace in LIB_CALLS or namespace == "df"

    def generate_parameter_list(self, parameters, builder, trailing_comma=False, suppress_linebreak=False):
        for last, parameter in lii(parameters):
            self.generate_function_call(parameter, builder, suppress_linebreak)
            if not last or trailing_comma:
                if self.config.getboolean("dash2html", "ProduceDebuggableCode") and self.is_lib_call(
                        parameter) and not suppress_linebreak:
                    builder.append_line(", ")
                else:
                    builder.append(", ")

    def generate_parameter(self, parameter, builder):
        value = self.format_value(parameter.get("value") or parameter.text) or parameter.get('input') or parameter.get(
            'state')
        name = parameter.get("name")
        if name is not None:
            builder.append(f"{name}=")
        builder.append(value)

    def generate_config(self, node, builder):
        key = node.get("key")
        type = node.get("type") or 'str'
        default = TYPE_CONVERSIONS[type](node.get("default"))
        key = ", ".join(key.split("."))
        builder.append(f"config.{CONFIG_TYPE_GETTER[type]}('{key}'")
        if default is not None:
            builder.append(f", fallback={default}")

        builder.append(")")

    def generate_update_code_new(self, node, builder, use_pages):
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
            input_candidates = node_map[parent_id].findall(".//d2h:parameter[@input]", namespaces={"d2h": "d2h"})
            inputs = []
            input_ids = []
            for input in input_candidates:
                input_node = input_map[input.get("input")]
                input_component = input_node.get("component_property")
                input_parent_id = parent_map[input_node].get("id")
                id = f"{input_component}:{input_parent_id}"
                if id not in input_ids:
                    inputs.append(input)
                    input_ids.append(id)

            state_candidates = node_map[parent_id].findall(".//d2h:parameter[@state]", namespaces={"d2h": "d2h"})
            states = []
            state_ids = []
            for input in state_candidates:
                input_node = input_map[input.get("state")]
                input_component = input_node.get("component_property")
                input_parent_id = parent_map[input_node].get("id")
                id = f"{input_component}:{input_parent_id}"
                if id not in input_ids and id not in state_ids:
                    states.append(input)
                    state_ids.append(id)

            builder.append_line(f"@{'' if use_pages else 'app.'}callback(")
            builder.push_indent()
            for last, output in lii(outputs_in_parent):
                builder.append(
                    f'Output(component_id="{parent_id}", component_property="{output.get("component_property")}")')
                if not last or len(inputs) > 0:
                    builder.append_line(",")

            for last, input in lii(inputs):
                input_node = input_map[input.get("input")]
                input_parent_id = parent_map[input_node].get("id")
                builder.append(
                    f'Input(component_id="{input_parent_id}", component_property="{input_node.get("component_property")}")')
                if not last or len(states) > 0:
                    builder.append_line(",")

            for last, input in lii(states):
                input_node = input_map[input.get("state")]
                input_parent_id = parent_map[input_node].get("id")
                builder.append(
                    f'State(component_id="{input_parent_id}", component_property="{input_node.get("component_property")}")')
                if not last:
                    builder.append_line(",")

            builder.append_line(")")
            builder.pop_indent()
            builder.append(f"def update_{parent_id}(")
            for last, input in lii(inputs):
                input_node = input_map[input.get("input")]
                builder.append(input_node.get("id"))
                if not last or len(states) > 0:
                    builder.append(", ")

            for last, states in lii(states):
                input_node = input_map[states.get("state")]
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
                    builder.append(self.format_value(value))
                elif len(output) > 0:
                    self.generate_function_call(output[0], builder, True)
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

    def generate_layout_code(self, node, builder):
        match = re.match("^(?:{(.*)})?(.*)$", node.tag)
        tag = match.group(2)
        namespace = match.group(1) or "html"
        if namespace == "html":
            tag = tag.capitalize()

        builder.append(f"{namespace}.{tag}(")
        children = [x for x in node if not (
                x.tag.startswith(f"{tag}.") or x.tag.startswith(f"{node.tag}.") or x.tag.startswith(
            "{d2h}") or x.tag.startswith("{dash}"))]
        nested_attributes = [x for x in node if x.tag.startswith(f"{tag}.") or x.tag.startswith(f"{node.tag}.")]
        has_args = False
        if len(children) > 0:
            builder.append_line("[")
            builder.push_indent()
            for last, child in lii(children):
                self.generate_layout_code(child, builder)
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
                builder.append(f"{key}={self.format_value(value)}")

            if not last_attrib:
                builder.append_line(", ")

        if len(nested_attributes) > 0 and (has_args or len(node.attrib) > 0):
            builder.append_line(",")

        for last, child in lii(nested_attributes):
            complex = bool(child.get("complex") or False)
            ctag = child.tag.split(".")[-1]
            if complex:
                builder.append(f"{ctag}=")
                self.generate_function_call(child[0], builder, False)
            else:
                builder.append(f"{ctag}={{")
                for last_item, item in lii(child):
                    builder.append(f'"{item.tag}": {self.format_value(item.text.strip())}{"" if last_item else ","}')
                builder.append("}")
                if not last:
                    builder.append_line(", ")
        builder.pop_indent()

        builder.append(")")
