with Dependz_Support.Adalog.Abstract_Relation;
use Dependz_Support.Adalog.Abstract_Relation;

procedure Main is
   Null_Rel : Relation;
begin
   Inc_Ref (Null_Rel);
   Print_Relation (Null_Rel);
   Dec_Ref (Null_Rel);
end Main;
