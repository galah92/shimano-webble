// Read-only Ghidra post-script: list recovered functions in an optional range.
//
// Usage with analyzeHeadless:
//   -scriptPath tools -postScript GhidraListFunctions.java
//   -scriptPath tools -postScript GhidraListFunctions.java 0xfffc0000 0xfffdd40f

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

public class GhidraListFunctions extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 0 && args.length != 2) {
            printerr("expected no arguments or start and end addresses");
            return;
        }
        Address start = args.length == 2 ? toAddr(args[0]) : null;
        Address end = args.length == 2 ? toAddr(args[1]) : null;
        if (start != null && end.compareTo(start) < 0) {
            printerr("end precedes start");
            return;
        }

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        int count = 0;
        while (functions.hasNext() && !monitor.isCancelled()) {
            Function function = functions.next();
            Address entry = function.getEntryPoint();
            if (start != null && (entry.compareTo(start) < 0 || entry.compareTo(end) > 0)) {
                continue;
            }
            println(entry + " " + function.getName() + " BODY " +
                function.getBody().getNumAddresses());
            count++;
        }
        println("FUNCTIONS " + count);
    }
}
