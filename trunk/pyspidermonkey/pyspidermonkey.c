
#include <Python.h>

#include <js_operating_system.h>

#include <jsatom.h>
#include <jsapi.h>
#include <jscntxt.h>
#include <jsdbgapi.h>
#include <jsfun.h>
#include <jsinterp.h>
#include <jsparse.h>
#include <jsscan.h>
#include <jsscope.h>
#include <jsstr.h>


#define ARRAY_COUNT(a) (sizeof(a) / sizeof(a[0]))


/** CONSTANTS
 */
static const char* tokens[] = {
	#define TOKEN(name) #name,
	#include "tokens.tbl"
	#undef TOKEN
};
JS_STATIC_ASSERT(ARRAY_COUNT(tokens) == TOK_LIMIT);

static const char* opcodes[] = {
	#define OPDEF(op,val,name,token,length,nuses,ndefs,prec,format) #op,
	#include <jsopcode.tbl>
	#undef OPDEF
};
JS_STATIC_ASSERT(ARRAY_COUNT(opcodes) == JSOP_LIMIT);

static const char *error_names[] = {
	#define MSG_DEF(name, number, count, exception, format) #name,
	#include <js.msg>
	#undef MSG_DEF
};
JS_STATIC_ASSERT(ARRAY_COUNT(error_names) == JSErr_Limit);


/** MODULE INITIALIZATION
 */

static PyObject*
module_traverse(PyObject *self, PyObject *args);

static PyMethodDef module_methods[] = {
	 {"traverse", module_traverse, METH_VARARGS,
	  "Parses \"script\" and calls \"push\" and \"pop\" for each node."},

	 {NULL, NULL, 0, NULL}		  /* Sentinel */
};

PyMODINIT_FUNC
initpyspidermonkey() {
	(void)Py_InitModule("pyspidermonkey", module_methods);
}

PyMODINIT_FUNC
initpyspidermonkey_d() {
	initpyspidermonkey();
}


/** MODULE IMPLEMENTATION
 */

typedef struct JSContextData {
	PyObject* error_callback;
} JSContextData;

static void
error_reporter(JSContext* cx, const char* message, JSErrorReport* report)
{
	JSContextData* data = JS_GetContextPrivate(cx);
	long int line = report->lineno - 1;
	long int col = -1;

	if (report->uclinebuf)
		col = report->uctokenptr - report->uclinebuf;

	// TODO: Check return value
	(void)PyObject_CallFunction(data->error_callback, "lls",
		line, col, error_names[report->errorNumber]);
}

static PyObject*
jsstring_to_py(JSString* jsstr) {
	PyObject* pystr;
	size_t i;

	pystr = PyUnicode_FromUnicode(NULL, jsstr->length);
	if (pystr) {
		for (i = 0; i < jsstr->length; i++)
			PyUnicode_AS_UNICODE(pystr)[i] = jsstr->chars[i];
	}

	return pystr;
}

static PyObject*
atom_to_string(JSAtom* atom) {
	if (!ATOM_IS_STRING(atom))
		return NULL;

	return jsstring_to_py(ATOM_TO_STRING(atom));
}

/* returns 0 on success and -1 on failure */
static int
traverse_node(JSContext* context, JSParseNode* jsnode, PyObject* tuple, int node_offset) {
	PyObject* kw = NULL;
	PyObject* kids = NULL;

	/* TODO: make sure no tuple item already exists */

	if (!jsnode) {
		Py_INCREF(Py_None);
		PyTuple_SET_ITEM(tuple, node_offset, Py_None);
		return 0;
	}

	/* pass in a dictionary of options */
	kw = PyDict_New();
	if (!kw)
		goto fail;

	PyTuple_SET_ITEM(tuple, node_offset, kw);

	if (PyDict_SetItemString(kw, "type", PyString_FromString(tokens[jsnode->pn_type])) == -1)
		goto fail;
	if (PyDict_SetItemString(kw, "node_index", Py_BuildValue("i", node_offset)) == -1)
		goto fail;

	/* pass the position */
	if (PyDict_SetItemString(kw, "start_row", Py_BuildValue("i", jsnode->pn_pos.begin.lineno-1)) == -1)
		goto fail;
	if (PyDict_SetItemString(kw, "start_col", Py_BuildValue("i", jsnode->pn_pos.begin.index)) == -1)
		goto fail;
	if (PyDict_SetItemString(kw, "end_row", Py_BuildValue("i", jsnode->pn_pos.end.lineno-1)) == -1)
		goto fail;
	if (PyDict_SetItemString(kw, "end_col", Py_BuildValue("i", jsnode->pn_pos.end.index)) == -1)
		goto fail;

	if ((jsnode->pn_type == TOK_NAME || jsnode->pn_type == TOK_DOT ||
		jsnode->pn_type == TOK_STRING) && ATOM_IS_STRING(jsnode->pn_atom)) {
		/* Convert the atom to a string. */
		if (PyDict_SetItemString(kw, "atom", atom_to_string(jsnode->pn_atom)) == -1)
			goto fail;
	}

	if (PyDict_SetItemString(kw, "opcode", PyString_FromString(opcodes[jsnode->pn_op])) == -1)
		goto fail;

	if (jsnode->pn_type == TOK_NUMBER) {
		if (PyDict_SetItemString(kw, "dval", Py_BuildValue("d", jsnode->pn_dval)) == -1)
			goto fail;
	}

	if (jsnode->pn_type == TOK_FUNCTION) {
		JSObject* object = ATOM_TO_OBJECT(jsnode->pn_funAtom);
		JSFunction* function = (JSFunction *) JS_GetPrivate(context, object);
		JSScope* scope = OBJ_SCOPE(object);
		JSScopeProperty* scope_property;
		PyObject* fn_name;
		PyObject* fn_args;
		uint32 i;
		JSPropertyDescArray props = {0, NULL};

		/* get the function name */
		if (function->atom) {
			fn_name = atom_to_string(function->atom);
		}
		else {
			Py_INCREF(Py_None);
			fn_name = Py_None;
		}
		if (PyDict_SetItemString(kw, "fn_name", fn_name) == -1)
			goto fail;

		/* get the function arguments */
		if (!JS_GetPropertyDescArray(context, object, &props))
			props.length = 0;

		fn_args = PyTuple_New(function->nargs);
		for (i = 0; i < props.length; i++) {
			PyObject* name;
			if ((props.array[i].flags & JSPD_ARGUMENT) == 0)
				continue;
			name = jsstring_to_py(JSVAL_TO_STRING(props.array[i].id));
			PyTuple_SET_ITEM(fn_args, props.array[i].slot, name);
		}

		/* Duplicate parameters are not included in the desc array. Go back and add them in. */
		for (scope_property = SCOPE_LAST_PROP(scope);
			scope_property != NULL;
			scope_property = scope_property->parent) {
			PyObject* name;

			if ((scope_property->flags & SPROP_IS_DUPLICATE) == 0)
				continue;
			if (PyTuple_GET_ITEM(fn_args, scope_property->shortid) != NULL)
				continue;

			name = atom_to_string(JSID_TO_ATOM(scope_property->id));
			PyTuple_SET_ITEM(fn_args, (uint16)scope_property->shortid, name);
		}
		if (PyDict_SetItemString(kw, "fn_args", fn_args) == -1)
			goto fail;
	}
	else if (jsnode->pn_type == TOK_RB) {
		PyObject* end_comma = PyBool_FromLong(jsnode->pn_extra & PNX_ENDCOMMA);
		if (PyDict_SetItemString(kw, "end_comma", end_comma) == -1)
			goto fail;
	}

	switch (jsnode->pn_arity) {
	case PN_FUNC:
		kids = PyTuple_New(1);
		if (traverse_node(context, jsnode->pn_body, kids, 0) == -1)
			return -1;
		break;

	case PN_LIST: {
		JSParseNode* p;
		int i;
		kids = PyTuple_New(jsnode->pn_count);
		for (i = 0, p = jsnode->pn_head; p; p = p->pn_next, i++) {
			if (traverse_node(context, p, kids, i) == -1)
				return -1;
		}
	}
	break;

	case PN_TERNARY:
		kids = PyTuple_New(3);
		if (traverse_node(context, jsnode->pn_kid1, kids, 0) == -1)
			return -1;
		if (traverse_node(context, jsnode->pn_kid2, kids, 1) == -1)
			return -1;
		if (traverse_node(context, jsnode->pn_kid3, kids, 2) == -1)
			return -1;
		break;

	case PN_BINARY:
		kids = PyTuple_New(2);
		if (traverse_node(context, jsnode->pn_left, kids, 0) == -1)
			return -1;
		if (traverse_node(context, jsnode->pn_right, kids, 1) == -1)
			return -1;
		break;

	case PN_UNARY:
		kids = PyTuple_New(1);
		if (traverse_node(context, jsnode->pn_kid, kids, 0) == -1)
			return -1;
		break;

	case PN_NAME:
		kids = PyTuple_New(1);
		if (traverse_node(context, jsnode->pn_expr, kids, 0) == -1)
			return -1;
		break;

	case PN_NULLARY:
		kids = PyTuple_New(0);
		break;
	}

	if (PyDict_SetItemString(kw, "kids", kids) == -1)
		goto fail;

	return 0;

fail:
	if (kw) {
		Py_XDECREF(kw);
	}
	return -1;
}

static PyObject*
module_traverse(PyObject *self, PyObject *args) {
	struct {
		const char* script;
		PyObject* kids;

		JSRuntime* runtime;
		JSContext* context;
		JSObject* global;
		JSTokenStream* token_stream;
		JSParseNode* jsnode;
		JSString* contents;

		JSContextData ctx_data;
	} m;
	const char* error;

	memset(&m, 0, sizeof(m));
	error = "encountered an unknown error";

	/* validate arguments */
	if (!PyArg_ParseTuple(args, "sO", &m.script, &m.ctx_data.error_callback))
		return NULL;

	if (!PyCallable_Check(m.ctx_data.error_callback)) {
		PyErr_SetString(PyExc_ValueError, "\"error\" must be callable");
		return NULL;
	}

	m.runtime = JS_NewRuntime(8L * 1024L * 1024L);
	if (m.runtime == NULL) {
		error = "cannot create runtime";
		goto cleanup;
	}

	m.context = JS_NewContext(m.runtime, 8192);
	if (m.context == NULL) {
		error = "cannot create context";
		goto cleanup;
	}
	JS_SetErrorReporter(m.context, error_reporter);
	JS_SetContextPrivate(m.context, &m.ctx_data);
	JS_ToggleOptions(m.context, JSOPTION_STRICT);

	m.contents = JS_NewStringCopyZ(m.context, m.script);
	if (m.contents == NULL) {
		error = "cannot create script contents";
		goto cleanup;
	}

	m.global = JS_NewObject(m.context, NULL, NULL, NULL);
	if (m.global == NULL) {
		error = "cannot create global object";
		goto cleanup;
	}

	if (!JS_InitStandardClasses(m.context, m.global)) {
		error = "cannot initialize standard classes";
		goto cleanup;
	}

	m.token_stream = js_NewBufferTokenStream(m.context, JS_GetStringChars(m.contents), JS_GetStringLength(m.contents));
	if (!m.token_stream) {
		error = "cannot create token stream";
		goto cleanup;
	}

	m.jsnode = js_ParseTokenStream(m.context, m.global, m.token_stream);
	if (!m.jsnode) {
		error = "parse error in file";
		goto cleanup;
	}

	m.kids = PyTuple_New(1);
	if (traverse_node(m.context, m.jsnode, m.kids, 0) == -1) {
		error = "";
		goto cleanup;
	}

	error = NULL;

cleanup:
	if (m.context)
		JS_DestroyContext(m.context);
	if (m.runtime)
		JS_DestroyRuntime(m.runtime);

	if (error) {
		if (*error) {
			PyErr_SetString(PyExc_StandardError, error);
		}
		return NULL;
	}
	Py_INCREF(m.kids);
	return m.kids;
}

