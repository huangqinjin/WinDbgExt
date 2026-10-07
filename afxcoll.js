//
// Copyright (c) 2026 Huang Qinjin (huangqinjin@gmail.com)
//
// Distributed under the Boost Software License, Version 1.0.
//    (See accompanying file LICENSE_1_0.txt or copy at
//          https://www.boost.org/LICENSE_1_0.txt)
//
"use strict";

function __dumpDebuggerObject(o) {
    host.diagnostics.debugLog(`targetLocation: ${o.targetLocation}\n`);
    host.diagnostics.debugLog(`targetSize: ${o.targetSize}\n`);
    host.diagnostics.debugLog(`runtimeTypedObject: ${o.runtimeTypedObject}\n`);
    host.diagnostics.debugLog(`targetType: ${o.targetType}\n`);
    host.diagnostics.debugLog(`address: ${o.address}\n`);
}

function __readCString(o) {
    if (typeof(o) !== "object" || o.targetType === undefined) {
        throw new Error("readCString requires a debugger object");
    }
    if (!o.targetType.toString().startsWith("ATL::CStringT")) {
        throw new Error(`readCString wrong type ${o.targetType}`);
    }
    var p = o.m_pszData;
    var d = host.evaluateExpression(`((ATL::CStringData*)${p.address})[-1]`);
    if (p.targetType.toString().startsWith("char")) {
        return host.memory.readString(p, d.nDataLength);
    }
    else {
        return host.memory.readWideString(p, d.nDataLength);
    }
}

function dumpCString(expr) {
    var o = host.evaluateExpression(expr);
    var s = __readCString(o);
    host.diagnostics.debugLog(`${s}\n`);
}

function dumpCStringArray(expr) {
    var o = host.evaluateExpression(expr);
    for (let i = 0; i < o.m_nSize; i++) {
        var s = __readCString(o.m_pData[i]);
        host.diagnostics.debugLog(`${s}\n`);
    }
}
