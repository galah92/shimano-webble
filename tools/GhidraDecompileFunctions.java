// Read-only Ghidra post-script: decompile one or more already identified functions.
//
// Usage with analyzeHeadless:
//   -scriptPath tools -postScript GhidraDecompileFunctions.java 0x23de2 +0x23b74
//
// Prefix an address with "+" to define a missed function in the scratch Ghidra
// project before decompiling it. The script neither embeds nor exports a vendor
// image; its output belongs in a private scratch directory with the image.

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class GhidraDecompileFunctions extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            printerr("expected at least one function address");
            return;
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(false);
        if (!decompiler.openProgram(currentProgram)) {
            printerr("could not initialize the decompiler");
            return;
        }

        try {
            for (String raw : args) {
                boolean createMissing = raw.startsWith("+");
                Address address = toAddr(createMissing ? raw.substring(1) : raw);
                Function function = getFunctionAt(address);
                if (function == null) {
                    function = currentProgram.getFunctionManager().getFunctionContaining(address);
                }
                if (function == null && createMissing) {
                    function = createFunction(address, null);
                }
                if (function == null) {
                    printerr("NO_FUNCTION " + address);
                    continue;
                }

                println("FUNCTION " + function.getName() + " " + function.getEntryPoint());
                DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    printerr("DECOMPILE_FAILED " + address + " " + result.getErrorMessage());
                    continue;
                }
                println(result.getDecompiledFunction().getC());
            }
        }
        finally {
            decompiler.dispose();
        }
    }
}
