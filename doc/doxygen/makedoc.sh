#!/bin/sh

# to generate Doxygen documentation under eman2/doc
# usage: makedoc.sh

which doxygen 2>/dev/null 1>/dev/null
if test ! $? = 0; then
    echo
    echo "Error: 'doxygen' is not found. Please install 'doxgen' first"
    echo
    exit 1
fi

echo -n "Start to generate Doxygen documentation. Be patient ... "
cd ../..
doxygen  doc/doxygen/Doxyfile
echo "Done"

rm -rf doc/doxygen_html
mv -f doc/html doc/doxygen_html

#echo "Documentation is at $PWD/doc/html/index.html"
