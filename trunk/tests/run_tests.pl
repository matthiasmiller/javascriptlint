#!/usr/bin/perl

use strict;
use File::Spec;

my ($script_volume,$script_directories,$script_file) = File::Spec->splitpath($0);
my $program_dir = File::Spec->catpath($script_volume,$script_directories,'');

# require a path to jsl
#
if (scalar(@ARGV) != 1) {
	die("Usage: $script_file <path to jsl>\n");
}
my $jsl_path = $ARGV[0];

# locate all files in the test folder
#
opendir(DIR, $program_dir) or die("Could not open directory $program_dir: $!");
my @files = grep(/\.(js|htm|html)$/,readdir(DIR));
closedir(DIR);

my $num_passed = 0;
foreach my $filename (@files) {
	my $full_path = File::Spec->catpath($script_volume,$script_directories,$filename);
	my $conf_path = File::Spec->catpath($script_volume,$script_directories,".jsl.conf");

	# open the path being validated
	open(FILE, $full_path) or die("Could not open $full_path: $!");
	my @contents = <FILE>;

	# look for special configuration directives
	my @conf = grep(s/\/\*conf:([^*]*)\*\//\1\n/g, @contents);
	open(FILE, ">$conf_path") or die("Could not open configuration file $conf_path: $!");
	print FILE join("",@conf);
	close FILE;

	# run the lint
	print "Testing $filename...\n";
	my $results = `$jsl_path --conf $conf_path --process $full_path --nologo --nofilelisting --nocontext --nosummary -output-format __LINE__,__ERROR_NAME__`;
	unlink $conf_path;
	die "Error executing $jsl_path" unless defined $results;

	my $this_passed = 1;
	foreach my $result (split("\n", $results)) {
		my ($line, $error) = split(",", $result);
		next unless $error; # for now, skip blank errors (such as inability to open file)

		# some warnings point beyond the end of the file
		$line = scalar(@contents) if $line > scalar(@contents);

		unless ($contents[$line-1] =~ s/\/\*warning//) {
			print "Error in $filename, line $line: $error\n";
			$this_passed = 0;
		}
	}
	for (my $i = 1; $i <= scalar(@contents); $i++) {
		if ($contents[$i-1] =~ /\/\*warning:([^*]*)\*\//) {
			print "Error in $filename, line $i: no $1 warning\n";
			$this_passed = 0;
		}
	}
	close(FILE);

	$num_passed++ if $this_passed;
}

print "Passed $num_passed of ", scalar(@files), " tests\n";
