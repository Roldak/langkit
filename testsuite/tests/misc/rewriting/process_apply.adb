with Ada.Text_IO; use Ada.Text_IO;

with GNATCOLL.VFS; use GNATCOLL.VFS;

with Dependz_Support.Diagnostics; use Dependz_Support.Diagnostics;
with Dependz_Support.Text;        use Dependz_Support.Text;
with Libfoolang.Analysis;         use Libfoolang.Analysis;

procedure Process_Apply
  (Handle         : in out Rewriting_Handle;
   Abort_On_Error : Boolean := True)
is
   Result : constant Apply_Result := Apply (Handle);
begin
   if not Result.Success then
      declare
         F : constant String :=
            +Create (+Get_Filename (Result.Unit)).Base_Name;
         Unit : constant Unit_Rewriting_Handle :=
            Libfoolang.Rewriting.Handle (Result.Unit);
      begin
         Put_Line ("Could not apply diff on the " & F & " unit:");
         for D of Result.Diagnostics loop
            Put_Line ("  " & To_Pretty_String (D));
         end loop;
         Put_Line (Image (Unparse (Root (Unit))));
         if Abort_On_Error then
            raise Program_Error;
         end if;
      end;
   end if;
end Process_Apply;
