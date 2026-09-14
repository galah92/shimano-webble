
METHOD SetInspectionModeOtherPanel::btnDestinationFactory_Click 0x38280
000C nop
000D call             get_ConnectedUnitList
0012 ldsfld           <>9__14_1
0017 dup
0018 brtrue.s         49
001A pop
001B ldsfld           <>9
0020 ldftn            <>c::<btnDestinationFactory_Click>b__14_1
0026 newobj           .ctor
002B dup
002C stsfld           <>9__14_1
0031 call             ?
0036 ldc.i4.0
0037 ceq
0039 stloc.1
003A ldloc.1
003B brfalse.s        75
003D nop
003E ldstr            'DUが接続されていません'
0043 call             Show
0048 pop
0049 br.s             151
004B call             get_ConnectedUnitList
0050 ldsfld           <>9__14_0
0055 dup
0056 brtrue.s         111
0058 pop
0059 ldsfld           <>9
005E ldftn            <>c::<btnDestinationFactory_Click>b__14_0
0064 newobj           .ctor
0069 dup
006A stsfld           <>9__14_0
006F call             ?
0074 call             ?
0079 stloc.0
007A ldloc.0
007B callvirt         get_SlotNo
0080 ldc.i4.0
0081 ldarg.0
0082 ldfld            cmbDestinationFactory
0087 callvirt         get_SelectedValue
008C unbox.any        Byte
0091 call             SetDestination
0096 pop
0097 ret

METHOD SetInspectionModeOtherPanel::btnDestinationOem_Click 0x38318
000C nop
000D call             get_ConnectedUnitList
0012 ldsfld           <>9__15_1
0017 dup
0018 brtrue.s         49
001A pop
001B ldsfld           <>9
0020 ldftn            <>c::<btnDestinationOem_Click>b__15_1
0026 newobj           .ctor
002B dup
002C stsfld           <>9__15_1
0031 call             ?
0036 ldc.i4.0
0037 ceq
0039 stloc.1
003A ldloc.1
003B brfalse.s        75
003D nop
003E ldstr            'DUが接続されていません'
0043 call             Show
0048 pop
0049 br.s             151
004B call             get_ConnectedUnitList
0050 ldsfld           <>9__15_0
0055 dup
0056 brtrue.s         111
0058 pop
0059 ldsfld           <>9
005E ldftn            <>c::<btnDestinationOem_Click>b__15_0
0064 newobj           .ctor
0069 dup
006A stsfld           <>9__15_0
006F call             ?
0074 call             ?
0079 stloc.0
007A ldloc.0
007B callvirt         get_SlotNo
0080 ldc.i4.1
0081 ldarg.0
0082 ldfld            cmbDestinationOem
0087 callvirt         get_SelectedValue
008C unbox.any        Byte
0091 call             SetDestination
0096 pop
0097 ret

METHOD SetInspectionModeOtherPanel::btnLightingTime_Click 0x383b0
000C nop
000D call             get_ConnectedUnitList
0012 ldsfld           <>9__16_1
0017 dup
0018 brtrue.s         49
001A pop
001B ldsfld           <>9
0020 ldftn            <>c::<btnLightingTime_Click>b__16_1
0026 newobj           .ctor
002B dup
002C stsfld           <>9__16_1
0031 call             ?
0036 ldc.i4.0
0037 ceq
0039 stloc.1
003A ldloc.1
003B brfalse.s        75
003D nop
003E ldstr            'DUが接続されていません'
0043 call             Show
0048 pop
0049 br.s             150
004B call             get_ConnectedUnitList
0050 ldsfld           <>9__16_0
0055 dup
0056 brtrue.s         111
0058 pop
0059 ldsfld           <>9
005E ldftn            <>c::<btnLightingTime_Click>b__16_0
0064 newobj           .ctor
0069 dup
006A stsfld           <>9__16_0
006F call             ?
0074 call             ?
0079 stloc.0
007A ldloc.0
007B callvirt         get_SlotNo
0080 ldarg.0
0081 ldfld            numLightingTime
0086 callvirt         get_Value
008B call             op_Explicit
0090 call             SetLightingTime
0095 pop
0096 ret

METHOD DriveUnitSetProgressPanel::setWorker_DoWork 0xcce2c
