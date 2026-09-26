// Read-only Ghidra post-script: report every reference to one or more addresses.
//
// Usage with analyzeHeadless:
//   -scriptPath tools -postScript GhidraFindAddressReferences.java 0x2000295f
//
// This intentionally emits only addresses, reference types, and containing
// function names. It does not export bytes from the input program.

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class GhidraFindAddressReferences extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            printerr("expected at least one target address");
            return;
        }

        for (String raw : args) {
            Address target = toAddr(raw);
            println("TARGET " + target);
            ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
            if (!references.hasNext()) {
                println("  NO_REFERENCES");
                continue;
            }
            for (Reference reference : references) {
                Address from = reference.getFromAddress();
                Function function = getFunctionContaining(from);
                String functionName = function == null ? "<no-function>" : function.getName();
                println("  FROM " + from + " TYPE " + reference.getReferenceType()
                    + " FUNCTION " + functionName);
            }
        }
    }
}
