// Read-only-image Ghidra post-script: linearly seed disassembly in a bounded
// scratch range and report instructions whose operands contain selected scalar
// values. The scratch project listing is modified; the imported binary is not.
//
// Usage with analyzeHeadless:
//   -scriptPath tools -postScript GhidraFindInstructionScalars.java 0x917c 0x1d400 0xb0 0xb4 0xbc
//   -scriptPath tools -postScript GhidraFindInstructionScalars.java 0x917c 0x1d400 --defined-only 0xb0 0xb4 0xbc

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.scalar.Scalar;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class GhidraFindInstructionScalars extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            printerr("expected start, end, and at least one scalar value");
            return;
        }
        Address start = toAddr(args[0]);
        Address end = toAddr(args[1]);
        if (end.compareTo(start) < 0 || end.subtract(start) > 0x400000) {
            printerr("invalid or excessive disassembly range");
            return;
        }
        boolean definedOnly = args[2].equals("--defined-only");
        int firstTarget = definedOnly ? 3 : 2;
        if (firstTarget >= args.length) {
            printerr("expected at least one scalar value");
            return;
        }
        Set<Long> targets = new HashSet<>();
        for (int i = firstTarget; i < args.length; i++) {
            targets.add(Long.decode(args[i]) & 0xffffffffL);
        }

        int seeds = 0;
        if (!definedOnly) {
            Address cursor = start;
            while (cursor.compareTo(end) <= 0 && !monitor.isCancelled()) {
                CodeUnit unit = currentProgram.getListing().getCodeUnitAt(cursor);
                if (unit == null) {
                    if (disassemble(cursor)) seeds++;
                    unit = currentProgram.getListing().getCodeUnitAt(cursor);
                }
                cursor = unit == null ? cursor.next() : unit.getMaxAddress().next();
            }
        }

        int matches = 0;
        Pattern immediate = Pattern.compile("(?i)#0x([0-9a-f]+)");
        InstructionIterator instructions = currentProgram.getListing().getInstructions(
            new AddressSet(start, end), true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            if (instruction.getAddress().compareTo(end) > 0) break;
            Set<Long> found = new HashSet<>();
            for (int operand = 0; operand < instruction.getNumOperands(); operand++) {
                for (Object object : instruction.getOpObjects(operand)) {
                    if (object instanceof Scalar) {
                        long value = ((Scalar)object).getUnsignedValue() & 0xffffffffL;
                        if (targets.contains(value)) found.add(value);
                    }
                }
            }
            // Some third-party processor modules render immediate operands but
            // do not expose them as Scalar objects. Preserve the structured
            // lookup above, then fall back to exact rendered immediates.
            Matcher matcher = immediate.matcher(instruction.toString());
            while (matcher.find()) {
                long value = Long.parseUnsignedLong(matcher.group(1), 16) & 0xffffffffL;
                if (targets.contains(value)) found.add(value);
            }
            if (!found.isEmpty()) {
                Function function = getFunctionContaining(instruction.getAddress());
                println(instruction.getAddress() + "  " + instruction + " VALUES " + found +
                    " FUNCTION " + (function == null ? "<no-function>" : function.getName()));
                matches++;
            }
        }
        println("SEEDS " + seeds + " MATCHES " + matches);
    }
}
