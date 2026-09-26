// Read-only Ghidra post-script: disassemble and print a bounded instruction
// window from a private scratch program.
//
// Usage with analyzeHeadless:
//   -scriptPath tools -postScript GhidraDumpInstructions.java 0xee40 160

// The script does not export memory bytes or modify the source image. Its
// output belongs in the private scratch directory used for analysis.

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class GhidraDumpInstructions extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            printerr("expected start address and positive instruction count");
            return;
        }
        Address start = toAddr(args[0]);
        int count = Integer.parseInt(args[1]);
        if (count < 1 || count > 2000) {
            printerr("instruction count must be between 1 and 2000");
            return;
        }
        disassemble(start);
        InstructionIterator instructions = currentProgram.getListing().getInstructions(start, true);
        int emitted = 0;
        while (instructions.hasNext() && emitted < count) {
            Instruction instruction = instructions.next();
            println(instruction.getAddress() + "  " + instruction.toString());
            emitted++;
        }
        println("INSTRUCTIONS " + emitted);
    }
}
