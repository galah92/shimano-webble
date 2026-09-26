// Read-only Ghidra post-script: find recovered functions whose decompiled C
// contains supplied literal terms. Vendor bytes and nonmatching functions are
// not printed.
//
// Usage with analyzeHeadless:
//   -scriptPath tools -postScript GhidraSearchDecompiled.java --any "switch(" "[1]" "[2]"
//   -scriptPath tools -postScript GhidraSearchDecompiled.java --all --print "switch(" "0xb0"

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.util.ArrayList;
import java.util.List;

public class GhidraSearchDecompiled extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        boolean requireAll = true;
        boolean printSource = false;
        List<String> terms = new ArrayList<>();
        for (String arg : args) {
            if (arg.equals("--all")) requireAll = true;
            else if (arg.equals("--any")) requireAll = false;
            else if (arg.equals("--print")) printSource = true;
            else terms.add(arg);
        }
        if (terms.isEmpty()) {
            printerr("expected at least one literal search term");
            return;
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(false);
        if (!decompiler.openProgram(currentProgram)) {
            printerr("could not initialize the decompiler");
            return;
        }

        int checked = 0;
        int matched = 0;
        try {
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function function = functions.next();
                DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
                checked++;
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    continue;
                }
                String source = result.getDecompiledFunction().getC();
                boolean hit = requireAll;
                for (String term : terms) {
                    if (requireAll) hit &= source.contains(term);
                    else hit |= source.contains(term);
                }
                if (!hit) continue;
                println("MATCH " + function.getEntryPoint() + " " + function.getName());
                if (printSource) println(source);
                matched++;
            }
        }
        finally {
            decompiler.dispose();
        }
        println("CHECKED " + checked + " MATCHED " + matched);
    }
}
