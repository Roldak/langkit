## vim: ft=makoada

with "gnatcoll";
with "gnatcoll_iconv";

library project Dependz_Support is

   type Build_Mode_Type is ("dev", "prod");
   Build_Mode : Build_Mode_Type := external ("BUILD_MODE", "dev");

   type Library_Kind_Type is ("static", "relocatable", "static-pic");
   Library_Kind_Param : Library_Kind_Type := external
     ("LIBRARY_TYPE", external ("LANGKIT_SUPPORT_LIBRARY_TYPE", "static"));

   for Languages use ("Ada");
   for Library_Name use "dependz_support";
   for Library_Kind use Library_Kind_Param;
   for Library_Interface use
     ("Dependz_Support",
      "Dependz_Support.Adalog",
      "Dependz_Support.Adalog.Abstract_Relation",
      "Dependz_Support.Adalog.Debug",
      "Dependz_Support.Adalog.Eq_Same",
      "Dependz_Support.Adalog.Logic_Ref",
      "Dependz_Support.Adalog.Logic_Var",
      "Dependz_Support.Adalog.Main_Support",
      "Dependz_Support.Adalog.Generic_Main_Support",
      "Dependz_Support.Adalog.Operations",
      "Dependz_Support.Adalog.Predicates",
      "Dependz_Support.Adalog.Pure_Relations",
      "Dependz_Support.Adalog.Relations",
      "Dependz_Support.Adalog.Solver",
      "Dependz_Support.Adalog.Unify",
      "Dependz_Support.Adalog.Unify_Lr",
      "Dependz_Support.Adalog.Unify_One_Side",
      "Dependz_Support.Array_Utils",
      "Dependz_Support.Boxes",
      "Dependz_Support.Generic_Bump_Ptr",
      "Dependz_Support.Bump_Ptr",
      "Dependz_Support.Bump_Ptr_Vectors",
      "Dependz_Support.Cheap_Sets",
      "Dependz_Support.Diagnostics",
      "Dependz_Support.Functional_Lists",
      "Dependz_Support.Hashes",
      "Dependz_Support.Images",
      "Dependz_Support.Iterators",
      "Dependz_Support.Lexical_Env",
      "Dependz_Support.Packrat",
      "Dependz_Support.Relative_Get",
      "Dependz_Support.Slocs",
      "Dependz_Support.Symbols",
      "Dependz_Support.Text",
      "Dependz_Support.Token_Data_Handlers",
      "Dependz_Support.Types",
      "Dependz_Support.Tree_Traversal_Iterator",
      "Dependz_Support.Vectors");

   for Source_Dirs use (${string_repr(source_dir)});
   for Library_Dir use "../dependz_support." & Library_Kind_Param;
   for Object_Dir use "../../obj/dependz_support." & Library_Kind_Param;

   Common_Ada_Cargs := ("-gnatwa", "-gnatyg");

   package Compiler is
      case Build_Mode is
         when "dev" =>
            for Default_Switches ("Ada") use
               Common_Ada_Cargs & ("-g", "-O0", "-gnatwe", "-gnata");

         when "prod" =>
            --  Debug information is useful even with optimization for
            --  profiling, for instance.
            for Default_Switches ("Ada") use
               Common_Ada_Cargs & ("-g", "-Ofast", "-gnatp");
      end case;
   end Compiler;

end Dependz_Support;
