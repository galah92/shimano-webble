
METHOD Shimano.EtubeDataLinks.DUUnitDataLink::SetLightingTime RVA=0xe16c
000C nop
000D ldarg.1
000E call               GetBytes
0013 stloc.0
0014 ldc.i4.4
0015 newarr             Byte
001A dup
001B ldtoken            D9BE6524A5F5047DB5866813ACF3277892A7A30A
0020 call               InitializeArray
0025 stloc.1
0026 ldloc.0
0027 ldc.i4.0
0028 ldloc.1
0029 ldc.i4.0
002A ldloc.0
002B ldlen
002C conv.i4
002D call               Copy
0032 nop
0033 ldarg.0
0034 ldc.i4.s           22
0036 ldc.i4             160
003B ldloc.1
003C call               Shimano.EtubeDataLinks.UnitCommandSetting::Make
0041 ldstr              'DCC_CMD_PU_MD_LIGHTING_TIME_SET'
0046 callvirt           Shimano.EtubeDataLinks.UnitCommandSetting::SetCommandName
004B ldsfld             <>9__43_0
0050 dup
0051 brtrue.s           106
0053 pop
0054 ldsfld             <>9
0059 ldftn              <>c::<SetLightingTime>b__43_0
005F newobj             .ctor
0064 dup
0065 stsfld             <>9__43_0
006A callvirt           Shimano.EtubeDataLinks.UnitCommandSetting::SetSendDataParamReader
006F stloc.2
0070 ldloc.2
0071 call               Shimano.EtubeDataLinks.EtubeDataLinksUnitCommand::SendReceiveUnitCommand
0076 stloc.3
0077 ldloc.3
0078 callvirt           get_Result
007D ldc.i4.1
007E ceq
0080 stloc.s            local(0x0004)
0082 br.s               132
0084 ldloc.s            local(0x0004)
0086 ret

METHOD Shimano.EtubeDataLinks.DUUnitDataLink::SetDestination RVA=0xe2a4
000C nop
000D ldarg.0
000E ldarg.1
000F ldarg.2
0010 ldc.i4.0
0011 call               Shimano.EtubeDataLinks.DUUnitDataLink::SetDestination
0016 stloc.0
0017 br.s               25
0019 ldloc.0
001A ret

METHOD Shimano.EtubeDataLinks.DUUnitDataLink::SetDestination RVA=0xe2c0
000C nop
000D ldc.i4.4
000E newarr             Byte
0013 dup
0014 ldtoken            D9BE6524A5F5047DB5866813ACF3277892A7A30A
0019 call               InitializeArray
001E stloc.0
001F ldloc.0
0020 ldc.i4.0
0021 ldarg.1
0022 stelem.i1
0023 ldloc.0
0024 ldc.i4.1
0025 ldarg.2
0026 stelem.i1
0027 ldarg.0
0028 ldc.i4.s           22
002A ldc.i4             168
002F ldloc.0
0030 call               Shimano.EtubeDataLinks.UnitCommandSetting::Make
0035 ldstr              'DCC_CMD_PU_MD_DESTINATION_SET'
003A callvirt           Shimano.EtubeDataLinks.UnitCommandSetting::SetCommandName
003F ldsfld             <>9__46_0
0044 dup
0045 brtrue.s           94
0047 pop
0048 ldsfld             <>9
004D ldftn              <>c::<SetDestination>b__46_0
0053 newobj             .ctor
0058 dup
0059 stsfld             <>9__46_0
005E callvirt           Shimano.EtubeDataLinks.UnitCommandSetting::SetSendDataParamReader
0063 stloc.1
0064 ldloc.1
0065 call               Shimano.EtubeDataLinks.EtubeDataLinksUnitCommand::SendReceiveUnitCommand
006A stloc.2
006B ldloc.2
006C callvirt           get_Result
0071 ldc.i4.1
0072 ceq
0074 stloc.3
0075 ldarg.3
0076 stloc.s            local(0x0004)
0078 ldloc.s            local(0x0004)
007A brfalse.s          139
007C nop
007D ldloc.3
007E brtrue.s           136
0080 ldloc.2
0081 call               Shimano.EtubeDataLinks.DUUnitDataLink::IsInvalidErr
0086 br.s               137
0088 ldc.i4.1
0089 stloc.3
008A nop
008B ldloc.3
008C stloc.s            local(0x0005)
008E br.s               144
0090 ldloc.s            local(0x0005)
0092 ret

METHOD <>c::<SetLightingTime>b__43_0 RVA=0x5d6b3
0001 ldc.i4.2
0002 newarr             String
0007 dup
0008 ldc.i4.0
0009 ldstr              'lighting_time'
000E stelem.ref
000F dup
0010 ldc.i4.1
0011 ldstr              '0x{0:X4}'
0016 ldarg.1
0017 ldc.i4.0
0018 call               ToUInt16
001D box                UInt16
0022 call               Format
0027 stelem.ref
0028 ret

METHOD <>c::<SetDestination>b__46_0 RVA=0x5d6dc
000C ldc.i4.4
000D newarr             String
0012 dup
0013 ldc.i4.0
0014 ldstr              'destination_rewrite'
0019 stelem.ref
001A dup
001B ldc.i4.1
001C ldstr              '0x{0:X2}'
0021 ldarg.1
0022 ldc.i4.0
0023 ldelem.u1
0024 box                Byte
0029 call               Format
002E stelem.ref
002F dup
0030 ldc.i4.2
0031 ldstr              'destination'
0036 stelem.ref
0037 dup
0038 ldc.i4.3
0039 ldstr              '0x{0:X2}'
003E ldarg.1
003F ldc.i4.1
0040 ldelem.u1
0041 box                Byte
0046 call               Format
004B stelem.ref
004C ret
