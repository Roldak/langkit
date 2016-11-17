## vim: filetype=makoada

with Ada.Unchecked_Deallocation;

with ${_self.ada_api_settings.lib_name}.AST;
use ${_self.ada_api_settings.lib_name}.AST;

package ${_self.ada_api_settings.lib_name}.Unit_Files is

   type Unit_File_Provider_Interface is interface;
   type Unit_File_Provider_Access is
      access Unit_File_Provider_Interface'Class;
   type Unit_File_Provider_Access_Cst is
      access constant Unit_File_Provider_Interface'Class;
   ${ada_doc('langkit.unit_file_provider_type', 3)}

   function Get_File
     (Provider : Unit_File_Provider_Interface;
      Node     : ${root_node_type_name})
      return String is abstract;
   ${ada_doc('langkit.unit_file_provider_get_file', 3)}

   procedure Destroy is new Ada.Unchecked_Deallocation
     (Unit_File_Provider_Interface'Class, Unit_File_Provider_Access);

end ${_self.ada_api_settings.lib_name}.Unit_Files;
