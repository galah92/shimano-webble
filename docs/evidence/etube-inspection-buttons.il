
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
; Selected ordering excerpt. The ordinary apply worker reaches tire
; circumference first. Lighting time is a later, conditional write.
0171 ldarg.0
0172 call             get_TargetUnit
0177 callvirt         get_SlotNo
017C ldarg.0
017D call             get_TireCircumference
0182 call             SetTireCircumference
; ... unrelated drive-unit setters omitted ...
043B ldarg.0
043C ldfld            fwVersion
0441 ldarg.0
0442 call             get_TargetUnit
0447 callvirt         get_UnitSpec
044C callvirt         get_ModelNo
0451 call             IsSupportedVersionToLightingTime
0456 brfalse.s        1128
0458 ldarg.0
0459 call             get_isLightingTimeExceeded
045E brtrue.s         1128
0460 ldarg.0
0461 call             get_isLightingTimeSettingChanged
046B ldloc.s          local(0x0014)
046D brfalse.s        1187
0470 ldarg.0
0471 call             get_TargetUnit
0476 callvirt         get_SlotNo
047B ldarg.0
047C call             get_LightingTime
0481 call             SetLightingTime
