"""REST-based Node Module helper classes."""


from sila2.server import SilaServer, FeatureImplementationBase
from sila2.framework import Feature
import inspect
import tempfile
import types
from typing import Callable, Any
from madsci.node_module.helpers import action
from madsci.node_module.abstract_node_module import AbstractNode
import xml.etree.ElementTree as ET
from uuid import uuid4
sila_basic_datatypes = {
    "string": "String",
    "int": "Integer",
    "float": "Real",
    "bool": "Boolean",
    "datetime.time": "Time",
    "datetime.date": "Date",
    "datetime.datetime": "Timestamp"
}

sila_derived_datatypes = {
    "list": "List",
}

class SubServer(SilaServer):
    def __init__(self):
        super().__init__(
                    server_name="test",
                    server_description='test',
                    server_type="ExampleDevice",
                    server_version="0.1.0",
                    server_vendor_url="https://github.com/AD-SDL/MADSci",
                    server_uuid=uuid4(),
                )

def constructor(cls, server: SubServer, *args: Any, **kwargs: Any) -> None:
    """Constructor for the dynamically created class."""
    cls.super().__init__(server, *args, **kwargs)
class SilaNode(AbstractNode):
    """REST-based node implementation with better OpenAPI documentation and result handling."""
    def __init__(self, *args: Any, **kwargs: Any) -> "RestNode":
        """Initialize the node class."""
        super().__init__(*args, **kwargs)
        self.node_info.node_url = getattr(self.config, "node_url", None)
        path = self.generate_feature_xml()
        print(path)
        feature = Feature(path)
        keywords = {}
        for action_name, action in self.action_handlers.items():
            keywords["ABC"] = action
        # # keywords["__init__"] = lambda self, server: super().__init__(self, server)
        # keywords["__init_subclass__"] = lambda self, server: super().__init__(self, server)
        SilaClass = types.new_class("SilaClass", (FeatureImplementationBase, ), exec_body=lambda ns: ns.update(keywords))
        self.server = SubServer()
        new_class = SilaClass(self.server)
        self.server.set_feature_implementation(feature, new_class)
        
    def start(self):
        self.server.start_insecure("0.0.0.0", 3011)   
        self.server.grpc_server.wait_for_termination()
        self.server.stop()

    def generate_feature_xml(self):
        root = ET.Element("Feature", attrib={
            "xmlns": "http://www.sila-standard.org",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "Category": "examples",
            "FeatureVersion": "1.0",
            "MaturityLevel": "Draft",
            "Originator": "org.madsci",
            "SiLA2Version": "1.0",
            "xsi:schemaLocation": "http://www.sila-standard.org https://gitlab.com/SiLA2/sila_base/raw/master/schema/FeatureDefinition.xsd"
        })
        id = ET.SubElement(root, "Identifier")
        id.text = "A" + self.node_info.node_id
        name = ET.SubElement(root, "DisplayName")
        name.text = self.node_info.node_name
        description = ET.SubElement(root, "Description")
        description.text = self.node_info.node_description
        for action_name, action in self.node_info.actions.items():
            command_elem = ET.SubElement(root, "Command")
            command_id = ET.SubElement(command_elem, "Identifier")
            command_id.text = "ABC"
            command_name = ET.SubElement(command_elem, "DisplayName")
            command_name.text = action_name
            command_description = ET.SubElement(command_elem, "Description")
            command_description.text = action.description
            command_observable = ET.SubElement(command_elem, "Observable")
            command_observable.text = "No"
            for parameter_name, parameter in action.args.items():
                parameter_elem = ET.SubElement(command_elem, "Parameter")
                parameter_id = ET.SubElement(parameter_elem, "Identifier")
                parameter_id.text = "ABD"
                parameter_name_elem = ET.SubElement(parameter_elem, "DisplayName")
                parameter_name_elem.text = parameter_name
                parameter_description = ET.SubElement(parameter_elem, "Description")
                parameter_description.text = parameter.description
                parameter_type = ET.SubElement(parameter_elem, "DataType")
                if parameter.argument_type in sila_basic_datatypes:
                    parameter_basic = ET.SubElement(parameter_type, "Basic")
                    parameter_basic.text = sila_basic_datatypes[parameter.argument_type]
                elif parameter.argument_type in sila_derived_datatypes:
                    parameter_complex = ET.SubElement(parameter_type, "Derived")
                    parameter_basic.text = sila_derived_datatypes[parameter.argument_type]
                else: 
                    parameter_basic = ET.SubElement(parameter_type, "Basic")
                    parameter_basic.text = "Any"
            if len(action.results) > 0:
                command_results = ET.SubElement(command_elem, "Response")
                result_id = ET.SubElement(command_results, "Identifier")
                result_id.text = "BCD"
                result_name = ET.SubElement(command_results, "DisplayName")
                result_name.text = "result"
                result_description = ET.SubElement(command_results, "Description")
                result_description.text = parameter.description
                result_type = ET.SubElement(command_results, "DataType")
                result_basic = ET.SubElement(result_type, "Basic")
                result_basic.text = "Any"
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            tree = ET.ElementTree(root)
            tree.write(temp_file.name, encoding="utf-8", xml_declaration=True)
            temp_file_path = temp_file.name
        return temp_file_path
    @action
    def get_node_info(self, test: "str"):
        """Return the node information."""
        return "test"
                
            
if __name__ == "__main__":
    node = SilaNode()
    node.start()
                


                        
                                     
